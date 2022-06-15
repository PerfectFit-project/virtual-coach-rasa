from enum import Enum


class Phases(str, Enum):
    PREPARATION = 'preparation'
    EXECUTION = 'execution'
    LAPSE = 'lapse'


class PreparationDialogs(str, Enum):
    PROFILE_CREATION = 'profile_creation'
    MEDICATION_TALK = 'medication_talk'
    COLD_TURKEY = 'cold_turkey'
    PLAN_QUIT_START_DATE = 'plan_quit_start_date'
    FUTURE_SELF = 'future_self_preparation'
    GOAL_SETTING = 'goal_setting'


class PreparationDialogsTriggers(str, Enum):
    PROFILE_CREATION = 'EXTERNAL_trigger_profile_creation'
    MEDICATION_TALK = 'EXTERNAL_trigger_medication_talk'
    COLD_TURKEY = 'EXTERNAL_trigger_cold_turkey'
    PLAN_QUIT_START_DATE = 'EXTERNAL_trigger_plan_quit_start'
    FUTURE_SELF = 'EXTERNAL_trigger_mental_contrasting'
    GOAL_SETTING = 'EXTERNAL_trigger_goal_setting'
