import logging
from rasa_sdk import Action, Tracker
from typing import Any, Dict, Text, Optional
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict


class ValidateActivityUsefullnessForm(FormValidationAction):
    '''
    https://rasa.com/docs/action-server/next/validation-action/
    runs when the form specified in its name is activated
    '''

    def name(self) -> Text:
        return 'validate_activity_usefulness_form'

# We can implement this directly but not needed for FormValidationAction
#    async def run(self, dispatcher, tracker, domain):
#        return {"activity_useful_rating",self.getVal()}

    def validate_activity_useful_rating(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """
        You can implement a Custom Action validate_<form_name> 
        to validate any extracted slots. 
        Make sure to add this action to the actions section of your domain:
        """
        #dispatcher.utter_message(response="validating your answer")
        logging.info("validating activity rating")
        val=self.getVal(slot_value)
        if val==None:
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
        # if val=None, this indicates to rasa the value is not known yet.
        return { "activity_useful_rating": val }

    def getVal(self, value:str) -> Optional[int]:
        '''
        return True iff value text can be cconverted to int in [1,4]
        '''
        try:
            val = int(value)
        except ValueError:
            return None
        if val < 1 or val > 4:
            return None
        return val
    