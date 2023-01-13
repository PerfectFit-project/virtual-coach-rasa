import string


def validate_int_type(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def validate_list(response: str, min_val: int, max_val: int) -> bool:
    try:
        value = list(map(int, response.split()))
    except ValueError:
        return False
    else:
        if min(value) < min_val or max(value) > max_val:
            return False
        return True


def validate_long_enough_response_words(response: str, min_length: int) -> bool:
    if response is None:
        return False
    return len(simple_sanitize_input(response).split()) > min_length


def validate_long_enough_response_chars(response: str, min_length: int) -> bool:
    if len(response) >= min_length:
        return True
    return False


def validate_number_in_range_response(n_min: int, n_max: int, response: str) -> bool:
    try:
        value = int(response)
    except ValueError:
        return False
    if (value < n_min) or (value > n_max):
        return False
    return True


def validate_yes_no_answer(response: str) -> bool:
    if response.lower() in ['Ja', 'ja', 'ja.', 'Nee', 'nee', "nee."]:
        return True
    return False


def simple_sanitize_input(value):
    return value.translate({c: "" for c in string.punctuation})
