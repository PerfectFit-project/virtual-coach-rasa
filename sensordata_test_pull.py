import Rasa_Bot.actions.helper
from datetime import datetime



id = 43895
start = datetime(2023, 4, 15)
end = datetime(2023, 4, 19)

num_steps = Rasa_Bot.actions.helper.get_steps_data(43895, start, end)