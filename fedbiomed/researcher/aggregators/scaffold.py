"""Scaffold Aggregator."""

import copy
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Union

import numpy as np
import torch

from fedbiomed.common.constants import TrainingPlans
from fedbiomed.common.exceptions import FedbiomedAggregatorError
from fedbiomed.common.training_plans import BaseTrainingPlan

from fedbiomed.researcher.aggregators.aggregator import Aggregator
from fedbiomed.researcher.aggregators.functional import weighted_sum
from fedbiomed.researcher.aggregators.functional import initialize
from fedbiomed.researcher.datasets import FederatedDataSet
from fedbiomed.researcher.responses import Responses


class Scaffold(Aggregator):
    """
    Defines the Scaffold strategy

    Attributes:
     - aggregator_name(str): name of the aggregator
     - server_lr (float): value of the server learning rate
     - nodes_correction_states(Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]]): corrections
     parameters obtained for each client
    """

    def __init__(self, server_lr: float = .01, fds: Optional[FederatedDataSet] = None):
        """Constructs `Scaffold` object as an instance of [`Aggregator`]
        [fedbiomed.researcher.aggregators.Aggregator].

        Despite being an algorithm of choice for federated learning, it is observed that FedAvg
        suffers from `client-drift` when the data is heterogeneous (non-iid), resulting in unstable and slow
        convergence. SCAFFOLD uses control variates (variance reduction) to correct for the `client-drift` in its local
        updates.
        Intuitively, SCAFFOLD estimates the update direction for the server model (c) and the update direction for each
        client (c_i).
        The difference (c - c_i) is then an estimate of the client-drift which is used to correct the local update.

        References:
        [Scaffold: Stochastic Controlled Averaging for Federated Learning][https://arxiv.org/abs/1910.06378]
        [TCT: Convexifying Federated Learning using Bootstrapped Neural
        Tangent Kernels][https://arxiv.org/pdf/2207.06343.pdf]

        Args:
            server_lr (float): server's (or Researcher's) learning rate. Defaults to .01.
            fds (FederatedDataset, optional): FederatedDataset obtained after a `search` request. Defaults to None.

        """
        super().__init__()
        self.aggregator_name: str = "Scaffold"
        if server_lr == 0.:
            raise FedbiomedAggregatorError("SCAFFOLD Error: Server learning rate cannot be equal to 0")
        self.server_lr: float = server_lr
        self.nodes_correction_states: Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]] = {}
        self.global_state: Mapping[str, Union[torch.Tensor, np.ndarray]] = {}

        self.nodes_lr: Dict[str, List[float]] = {}
        if fds is not None:
            self.set_fds(fds)
        if self._aggregator_args is None:
            self._aggregator_args = {}
        #self.update_aggregator_params()

    def aggregate(self,
                  model_params: list,
                  weights: List[Dict[str, float]],
                  global_model: Mapping[str, Union[torch.Tensor, np.ndarray]],
                  training_plan: BaseTrainingPlan,
                  training_replies: Responses,
                  node_ids: Iterable[str],
                  n_updates: int = 1,
                  n_round: int = 0,
                  *args, **kwargs) -> Dict:
        """
        Aggregates local models coming from nodes into a global model, using SCAFFOLD algorithm (2nd option)
        [Scaffold: Stochastic Controlled Averaging for Federated Learning][https://arxiv.org/abs/1910.06378]

        Performed computations:
        -----------------------

        c_i(+) <- c_i - c + 1/(K*eta_l)(x - y_i)
        c <- c + 1/N * sum_S(c_i(+) - c_i)

        x <- x + eta_g/S * sum_S(y_i - x)

        where, according to paper notations
            c_i: correction state for node `i`;
            c: correction state at the beginning of round
            eta_g: server's learning rate
            eta_l: nodes learning rate (may be different from one node to another)
            N: total number of node participating to federated learning
            S: number of nodes considered during current round (S<=N)
            K: number of updates done during the round (ie number of data batches).
            x: global model parameters
            y_i: node i 's local model parameters

        Args:
            model_params (list): list of models parameters recieved from nodes
            weights (List[Dict[str, float]]): weights depciting sample proportions available
                on each node. Unused for Scaffold.
            global_model (Mapping[str, Union[torch.Tensor, np.ndarray]]): global model,
                ie aggregated model
            training_plan (BaseTrainingPlan): instance of TrainingPlan
            node_ids (Iterable[str]): iterable containing node_id (string) participating to the current round.
                its length should be lower or equal to
            n_updates (int, optional): number of updates (number of batch performed). Defaults to 1.
            n_round (int, optional): current round. Defaults to 0.

        Returns:
            Dict: aggregated parameters, ie mapping of layer names and layer values.
        """

        # Unpack input local model parameters to {node_id: {name: value, ...}, ...} format.
        model_params = {list(node_content.keys())[0]: list(node_content.values())[0] for node_content in model_params}
        # Compute the new aggregated model parameters.
        aggregated_parameters = {}
        for key, val in global_model.items():
            update = sum(params[key] for params in model_params.values()) / len(model_params)
            newval = (1 - self.server_lr) * val + self.server_lr * update
            aggregated_parameters[key] = newval
        # Gather the learning rates used by nodes, updating `self.nodes_lr`.
        self.set_nodes_learning_rate_after_training(training_plan, training_replies, n_round)
        # At round 0, initialize zero-valued correction states.
        if n_round == 0:
            self.init_correction_states(global_model, node_ids)
        # Update correction states.
        self.update_correction_states(model_params, global_model, n_updates)
        # Return aggregated parameters.
        return aggregated_parameters

    def create_aggregator_args(self,
                               global_model: Mapping[str, Union[torch.Tensor, np.ndarray]],
                               node_ids: Iterator[str]) -> Tuple[Dict, Dict]:
        """Sends additional arguments for aggregator. For scaffold, it is mainly correction states

        Args:
            global_model (Mapping[str, Union[torch.Tensor, np.ndarray]]): aggregated model
            node_ids (Iterator[str]): iterable that contains strings of nodes id that have particpated to
                the round

        Returns:
            Tuple[Dict, Dict]: first dictionary contains parameters that will be sent through MQTT message
                service, second dictionary parameters that will be sent through file exchange message.
                Aggregators args are dictionary mapping node_id to nodes parameters.
        """
        if not self.nodes_correction_states:
            self.init_correction_states(global_model, node_ids)
        aggregator_args_thr_msg, aggregator_args_thr_file = {}, {}
        for node_id in node_ids:
            # in case of a new node, use zero-valued local state
            if node_id not in self.nodes_correction_states:
                self.nodes_correction_states[node_id] = {
                    key: -val for key, val in self.global_state.items()
                }
            # pack information and parameters to send
            aggregator_args_thr_file[node_id] = {
                'aggregator_name': self.aggregator_name,
                'aggregator_correction': self.nodes_correction_states[node_id]
            }
            aggregator_args_thr_msg[node_id] = {
                'aggregator_name': self.aggregator_name
            }
        return aggregator_args_thr_msg, aggregator_args_thr_file

    def check_values(self, node_lrs: List[float], n_updates: int):
        """
        This method checks if all values are correct and have been set before using aggregator.
        Raises error otherwise
        This can prove usefull, so that user will have errors before performing first round of training

        Args:
            lr (float): _description_

        Raises:
            FedbiomedAggregatorError: _description_
        """
        # check if values are non zero
        if not node_lrs.any():
            raise FedbiomedAggregatorError(f"Learning rate(s) should be non-zero, but got {node_lrs} (in SCAFFOLD aggreagator)")
        if n_updates == 0 or int(n_updates) != float(n_updates):
            raise FedbiomedAggregatorError(f"n_updates should be a non zero integer, but got n_updates: {n_updates} in SCAFFOLD aggregator")
        if self._fds is None:
            raise FedbiomedAggregatorError(" Federated Dataset not provided, but needed for Scaffold. Please use `set_fds()`")
        # TODO: check if optimizer is SGD, otherwise, trigger warning

    def set_nodes_learning_rate_after_training(self, training_plan: BaseTrainingPlan,
                                               training_replies: List[Responses],
                                               n_round: int) -> Dict[str, List[float]]:
        """Gets back learning rate of optimizer from Node (if learning rate scheduler is used)

        Args:
            training_plan (BaseTrainingPlan): training plan instance
            training_replies (List[Responses]): training replies that must contain am `optimizer_args`
                entry and a learning rate
            n_round (int): number of rounds already performed

        Raises:
            FedbiomedAggregatorError: raised when setting learning rate has been unsuccessful

        Returns:
            Dict[str, List[float]]: dictionary mapping node_id and a list of float, as many as
                the number of layers contained in the model (in Pytroch, each layer can have a specific learning rate).
        """
        # to be implemented in a utils module (for pytorch optimizers)

        n_model_layers = len(training_plan.get_model_params())
        for node_id in self._fds.node_ids():
            lrs: List[float] = []

            if training_replies[n_round].get_index_from_node_id(node_id) is not None:
                # get updated learning rate if provided...
                node_idx: int = training_replies[n_round].get_index_from_node_id(node_id)
                lrs += training_replies[n_round][node_idx]['optimizer_args'].get('lr')

            else:
                # ...otherwise retrieve default learning rate
                lrs += training_plan.get_learning_rate()

            if len(lrs) == 1:
                # case where there is one learning rate
                lr = lrs * n_model_layers

            elif len(lrs) == n_model_layers:
                # case where there are several learning rates value
                lr = lrs
            else:

                raise FedbiomedAggregatorError("Error when setting node learning rate for SCAFFOLD: cannot extract node learning rate.")

            self.nodes_lr[node_id] = lr
        return self.nodes_lr

    def init_correction_states(self,
                               global_model: Mapping[str, Union[torch.Tensor, np.ndarray]],
                               node_ids: Iterable[str],
                               ):
        """Initialises correction_states variable for Scaffold

        Args:
            global_model (Mapping[str, Union[torch.Tensor, np.ndarray]]): global model mapping layer name to model
            parameters
            node_ids (Iterable[str]): iterable containing node_ids
        """
        # initialize nodes states with zeros tensors
        init_params = {key: initialize(tensor)[1] for key, tensor in global_model.items()}
        self.nodes_correction_states = {node_id: copy.deepcopy(init_params) for node_id in node_ids}
        self.global_state = init_params

    def update_correction_states(self,
                                 local_models: Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]],
                                 global_model: Mapping[str, Union[torch.Tensor, np.ndarray]],
                                 n_updates: int = 1,) -> None:
        """Updates correction states

        Proof:

        c <- c + S/N grad(c)
        c <- c + 1/N sum_i(c_i(+) - c_i)
        c <- c + 1/N * sum_i( 1/ (K * eta_l)(x - y_i) - c)

        where (according to Scaffold paper):
        c: is the correction term
        S: the number of nodes participating in the current round
        N: the total number of node participating in the experiment
        K: number of updates
        eta_l: nodes' learning rate
        x: global model before updates
        y_i: local model updates

        Args:
            local_models: Node-wise local model parameters after updates, as
                as {name: value} parameters mappings indexed by node id.
            global_model: Global model parameters (before updates), as a single
                {name: value} parameters mapping.
            n_updates: number of batches (or updates) performed during one round
                Referred to as `K` in the Scaffold paper. Defaults to 1.

        Raises:
            FedbiomedAggregatorError: if no FederatedDataset has been found.
        """
        # Gather the total number of nodes (not just participating ones).
        if self._fds is None:
            raise FedbiomedAggregatorError("Cannot run SCAFFOLD aggregator: No Federated Dataset set")
        total_nb_nodes = len(self._fds.node_ids())
        # Compute the node-wise average of corrected gradients (ACG_i).
        # i.e. (theta^t - theta_i^{t+1}) / (K * eta_l)
        local_state_updates = {}  # type: Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]]
        for node_id, params in local_models.items():
            local_state_updates[node_id] = {
                key: (global_model[key] - val) / (self.nodes_lr[node_id][idx] * n_updates)
                for idx, (key, val) in enumerate(params.items())
            }
        # Compute the shared state variable's update by averaging the former.
        global_state_update = {
            key: sum(state[key] for state in local_state_updates.values()) / total_nb_nodes
            for key in global_model
        }
        # Compute the updated shared state variable.
        # c^{t+1} = (1 - S/N)c^t + (1/N) sum_{i=1}^S ACG_i
        share = 1 - len(local_models) / total_nb_nodes
        global_state_new = {
            key: share * self.global_state[key] + val
            for key, val in global_state_update.items()
        }
        # Compute the difference between past and new shared state variables.
        global_state_diff = {
            key: self.global_state[key] - val
            for key, val in global_state_new.items()
        }
        # Compute the updated node-wise correction terms.
        for node_id in self._fds.node_ids():
            acg = local_state_updates.get(node_id, None)
            # Case when the node did not participate in the round.
            # d_i^{t+1} = d_i^t + c^t - c^{t+1}
            if acg is None:
                for key, val in self.nodes_correction_states[node_id].items():
                    self.nodes_correction_states[node_id][key] += global_state_diff[key]
            # Case when the node participated in the round
            # d_i^{t+1} = c_i^{t+1} - c^{t+1} = ACG_i - d_i^{t} - c^{t+1}
            else:

                for key, val in self.nodes_correction_states[node_id].items():
                    
                    self.nodes_correction_states[node_id][key] = (
                        local_state_updates[node_id][key] - val - global_state_new[key]
                    )
        # Assign the updated shared state.
        self.global_state = global_state_new

    def set_training_plan_type(self, training_plan_type: TrainingPlans) -> TrainingPlans:
        """
        Overrides `set_training_plan_type` from parent class.
        Checks the trainning plan type, and if it is SKlearnTrainingPlan,
        raises an error. Otherwise, calls parent method.

        Args:
            training_plan_type (TrainingPlans): training_plan type

        Raises:
            FedbiomedAggregatorError: raised if training_plan type has been set to SKLearn training plan

        Returns:
            TrainingPlans: trainijng plan type
        """
        if training_plan_type == TrainingPlans.SkLearnTrainingPlan:
            raise FedbiomedAggregatorError("Aggregator SCAFFOLD not implemented for SKlearn")
        training_plan_type = super().set_training_plan_type(training_plan_type)

        # TODO: trigger a warning if user is trying to use scaffold with something else than SGD
        return training_plan_type

    def save_state(self, training_plan: BaseTrainingPlan, breakpoint_path: str, global_model: Mapping[str, Union[torch.Tensor, np.ndarray]]) -> Dict[str, Any]:
        #aggregator_args_msg, aggregator_args_file = self.create_aggregator_args(global_model, self._fds.node_ids())

        return super().save_state(training_plan, breakpoint_path, global_model=global_model, node_ids=self._fds.node_ids())

    def load_state(self, state: Dict[str, Any] = None, training_plan: BaseTrainingPlan = None):
        super().load_state(state)
        self.server_lr = self._aggregator_args['server_lr']

        self.nodes_correction_states = {}
        for node_id in self._aggregator_args['aggregator_correction'].keys():
            arg_filename = self._aggregator_args['aggregator_correction'][node_id]

            self.nodes_correction_states[node_id] = training_plan.load(arg_filename)
            #self.nodes_correction_states[node_id].pop('aggregator_name')
