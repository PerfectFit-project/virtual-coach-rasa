
from rasa_sdk.forms import FormValidationAction


class ValidateActivityUsefullnessForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_activity_usefulness_form'

    def validate_rescheduling_option(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate rescheduling_option input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"activity_usefulness": None}

        return {"activity_usefulness": int(value)}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 4):
            return False
        return True
    