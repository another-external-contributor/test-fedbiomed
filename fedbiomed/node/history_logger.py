from typing import Union

from fedbiomed.common.message import NodeMessages
from fedbiomed.common.messaging import Messaging
from fedbiomed.node.environ import CLIENT_ID


class HistoryLogger:
    def __init__(self,
                 job_id: str,
                 researcher_id: str,
                 client: Messaging):
        self.history = {}
        self.job_id = job_id
        self.researcher_id = researcher_id
        self.messaging = client

    def add_scalar(self, key: str, value: Union[int, float], iteration: int):
        """Adds a value to the logger, and sends an 'AddReply'
        response to researcher

        Args:
            key (str): name value in logger to keep track with
            value (Union[int, float]):  recorded value
            iteration (int): current epoch iteration.
        """
        try:
            self.history[key][iteration] = value
        except (KeyError, AttributeError):
            self.history[key] = {iteration: value}

        self.messaging.send_message(NodeMessages.reply_create({
                                                               'client_id': CLIENT_ID,
                                                               'job_id': self.job_id,
                                                               'researcher_id': self.researcher_id,
                                                               'key': value,
                                                               'iteration': iteration,
                                                               "command": "add_scalar"
                                                               }).get_dict())
