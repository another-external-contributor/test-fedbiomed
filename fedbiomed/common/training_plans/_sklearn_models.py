import numpy as np

from sklearn.linear_model import SGDRegressor, SGDClassifier, Perceptron
from sklearn.naive_bayes import BernoulliNB, GaussianNB

from fedbiomed.common.constants import ErrorNumbers, TrainingPlans, ProcessTypes
from fedbiomed.common.exceptions import FedbiomedTrainingPlanError
from fedbiomed.common.logger import logger


from ._sklearn_training_plan import SKLearnTrainingPlan

class FedPerceptron(SKLearnTrainingPlan):
    def __init__(self, model_args: dict = {}):
        """
        Sklearn Perceptron model
        Args:
        - model_args: (dict, optional): model arguments. Defaults to {}
        """
        super().__init__(Perceptron,
                         self.training_routine_hook,
                         model_args,
                         verbose_possibility = True)

        # specific for Perceptron
        self.is_classification = True
        self._verbose_capture_option = True
        # Instantiate the model
        self.set_init_params()
        self.add_dependency([
                             "from sklearn.linear_model import Perceptron "
                             ])

    def training_routine_hook(self):
        """
        Training routine of Perceptron
        """
        (self.data, self.target) = self.training_data_loader
        classes = self.__classes_from_concatenated_train_test()
        if classes.shape[0] < 3:
            self._is_binary_classification = True

        self.model.partial_fit(self.data, self.target, classes=classes)

    def set_init_params(self):
        """
        Initialize the model parameter
        """
        self.param_list = ['intercept_','coef_']
        init_params = {
            'intercept_': np.array([0.]) if (self._model_args['n_classes'] == 2) else np.array(
                [0.] * self._model_args['n_classes']),
            'coef_': np.array([0.] * self._model_args['n_features']).reshape(1, self._model_args['n_features']) if (
                    self._model_args['n_classes'] == 2) else np.array(
                [0.] * self._model_args['n_classes'] * self._model_args['n_features']).reshape(self._model_args['n_classes'],
                                                                                   self._model_args['n_features'])
        }

        for p in self.param_list:
            setattr(self.model, p, init_params[p])

        for p in self.params_sgd:
            setattr(self.model, p, self.params_sgd[p])

    def __evaluate_loss(self,output,epoch) -> float:
        '''
        Evaluate the loss.
        Args:
        - output: output of the scikit-learn perceptron model during training
        - epoch: epoch number
        Returns: float: the loss captured in the output of its weighted average in case of mutliclass classification
        '''
        _loss_collector = self.__evaluate_loss_core(output,epoch)
        if not self._is_binary_classification:
            support = self._compute_support(self.target)
            loss = np.average(_loss_collector, weights=support)  # perform a weighted average
            logger.warning("Loss plot displayed on Tensorboard may be inaccurate (due to some plain" + \
                           " SGD scikit learn limitations)")
        else:
            loss = _loss_collector[-1]
        return loss


#======

class FedSGDRegressor(SKLearnTrainingPlan):
    def __init__(self, model_args):
        """
        Sklearn SGDRegressor model
        Args:
        - model_args: (dict, optional): model arguments. Defaults to {}
        """
        super().__init__(SGDRegressor,
                         self.training_routine_hook,
                         model_args,
                         verbose_possibility = True)

        # specific for SGDRegressor
        self._is_regression = True
        self._verbose_capture_option = True

        if 'verbose' not in model_args:
            self._model_args['verbose'] = 1

        # Instantiate the model
        self.set_init_params()

        self.add_dependency([
                             "from sklearn.linear_model import SGDRegressor "
                             ])

    def training_routine_hook(self):
        """
        Training routine of SGDRegressor
        """
        (data, target) = self.training_data_loader
        self.model.partial_fit(data, target)

    def set_init_params(self):
        """
        Initialize the model parameter
        """
        self.param_list = ['intercept_','coef_']
        init_params = {'intercept_': np.array([0.]),
                       'coef_': np.array([0.] * self._model_args['n_features'])}
        for p in self.param_list:
            setattr(self.model, p, init_params[p])

        for p in self.params_sgd:
            setattr(self.model, p, self.params_sgd[p])

    def __evaluate_loss(self,output,epoch) -> float:
        '''
        Evaluate the loss.
        Args:
        - output: output of the scikit-learn SGDRegressor model during training
        - epoch: epoch number
        Returns: float: the loss captured in the output
        '''
        _loss_collector = self.__evaluate_loss_core(output,epoch)
        return _loss_collector[-1]


#======

class FedSGDClassifier(SKLearnTrainingPlan):
    def __init__(self, model_args):
        """
        Sklearn SGDClassifier model
        Args:
        - model_args: (dict, optional): model arguments. Defaults to {}
        """

        super().__init__(SGDClassifier,
                         self.training_routine_hook,
                         model_args,
                         verbose_possibility = True)

        self.is_classification = True
        self._verbose_capture_option = True

        if 'verbose' not in model_args:
            self._model_args['verbose'] = 1

        # Instantiate the model
        self.set_init_params()

        self.add_dependency(["from fedbiomed.common.training_plans import FedPerceptron"
                             "from sklearn.linear_model import SGDClassifier "
                             ])

    def training_routine_hook(self):
        """
        Training routine of SGDClassifier
        """
        (self.data, self.target) = self.training_data_loader
        classes = self.__classes_from_concatenated_train_test()
        if classes.shape[0] < 3:
            self._is_binary_classification = True

        self.model.partial_fit(self.data, self.target, classes=classes)

    def set_init_params(self):
        """
        Initialize the model parameter
        """
        self.param_list = ['intercept_','coef_']
        init_params = {
            'intercept_': np.array([0.]) if (self._model_args['n_classes'] == 2) else np.array(
                [0.] * self._model_args['n_classes']),
            'coef_': np.array([0.] * self._model_args['n_features']).reshape(1, self._model_args['n_features']) if (
                    self._model_args['n_classes'] == 2) else np.array(
                [0.] * self._model_args['n_classes'] * self._model_args['n_features']).reshape(self._model_args['n_classes'],
                                                                                   self._model_args['n_features'])
        }

        for p in self.param_list:
            setattr(self.model, p, init_params[p])

        for p in self.params_sgd:
            setattr(self.model, p, self.params_sgd[p])

    def __evaluate_loss(self,output,epoch) -> float:
        '''
        Evaluate the loss.
        Args:
        - output: output of the scikit-learn SGDClassifier model during training
        - epoch: epoch number
        Returns: float: the loss captured in the output of its weighted average in case of mutliclass classification
        '''
        _loss_collector = self.__evaluate_loss_core(output,epoch)
        if not self._is_binary_classification:
            support = self._compute_support(self.target)
            loss = np.average(_loss_collector, weights=support)  # perform a weighted average
            logger.warning("Loss plot displayed on Tensorboard may be inaccurate (due to some plain" + \
                           " SGD scikit learn limitations)")
        else:
            loss = _loss_collector[-1]
        return loss

class FedBernoulliNB(SKLearnTrainingPlan):
    def __init__(self, model_args):
        """
        Sklearn BernoulliNB model
        Args:
        - model_args: (dict, optional): model arguments. Defaults to {}
        """
        super().__init__(BernoulliNB,
                         self.training_routine_hook,
                         model_args,
                         verbose_possibility = False)

        self.is_classification = True
        if 'verbose' in model_args:
            logger.error("[TENSORBOARD ERROR]: cannot compute loss for BernoulliNB "
                         ": it needs to be implemeted")
        self.add_dependency([
                             "from sklearn.naive_bayes  import BernoulliNB"
                             ])

    def training_routine_hook(self):
        """
        Training routine of BernoulliNB
        """
        (data, target) = self.training_data_loader
        classes = self.__classes_from_concatenated_train_test()
        if classes.shape[0] < 3:
            self._is_binary_classification = True

        self.model.partial_fit(data, target, classes=classes)


class FedGaussianNB(SKLearnTrainingPlan):
    def __init__(self, model_args):
        """
        Sklearn GaussianNB model
        Args:
        - model_args: (dict, optional): model arguments. Defaults to {}
        """
        super().__init__(GaussianNB,
                         self.training_routine_hook,
                         model_args,
                         verbose_possibility = False)
        self.is_classification = True
        if 'verbose' in model_args:
            logger.error("[TENSORBOARD ERROR]: cannot compute loss for GaussianNB "
                         ": it needs to be implemeted")

        self.add_dependency([
                             "from sklearn.naive_bayes  import GaussianNB"
                             ])

    def training_routine_hook(self):
        """
        Training routine of GaussianNB
        """
        (data, target) = self.training_data_loader
        classes = self.__classes_from_concatenated_train_test()
        if classes.shape[0] < 3:
            self._is_binary_classification = True

        self.model.partial_fit(data, target, classes=classes)



#############################################################################################3
class FedMultinomialNB(SKLearnTrainingPlan):

    #
    # or simply do not provide this file
    #

    def __init__(self, model_args):

        raise("model not implemented yet")

    def training_routine_hook(self):
        pass

class FedPassiveAggressiveClassifier(SKLearnTrainingPlan):

    #
    # or simply do not provide this file
    #

    def __init__(self, model_args):

        raise("model not implemented yet")

    def training_routine_hook(self):
        pass

class FedPassiveAggressiveRegressor(SKLearnTrainingPlan):

    #
    # or simply do not provide this file
    #

    def __init__(self, model_args):

        raise("model not implemented yet")

    def training_routine_hook(self):
        pass

class FedMiniBatchKMeans(SKLearnTrainingPlan):

    #
    # or simply do not provide this file
    #

    def __init__(self, model_args):

        raise("model not implemented yet")

    def training_routine_hook(self):
        pass

class FedMiniBatchDictionaryLearning(SKLearnTrainingPlan):

    #
    # or simply do not provide this file
    #

    def __init__(self, model_args):

        raise("model not implemented yet")

    def training_routine_hook(self):
        pass