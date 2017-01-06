# -*- coding: utf-8 -*-
mock_spell_activity_id = 1

mock_refusal_episode_first = {
    'count': 1,
    'first_refusal_date_terminated': '2017-01-03 17:49:11.36621',
    'freq_date_terminated': None,
    'freq_state': None,
    'freq_terminate_uid': None,
    'review_date_terminated': None,
    'review_state': None,
    'review_terminate_uid': None,
    'spell_activity_id': 10
}
mock_refusal_episode_second = {
    'count': 1,
    'first_refusal_date_terminated': '2017-01-03 17:49:13.36621',
    'freq_date_terminated': None,
    'freq_state': None,
    'freq_terminate_uid': None,
    'review_date_termninated': None,
    'review_state': None,
    'review_terminate_uid': None,
    'spell_activity_id': 10
}
mock_refusal_episode_third = {
    'count': 1,
    'first_refusal_date_terminated': '2017-01-03 17:49:14.36621',
    'freq_date_terminated': None,
    'freq_state': None,
    'freq_terminate_uid': None,
    'review_date_termninated': None,
    'review_state': None,
    'review_terminate_uid': None,
    'spell_activity_id': 10
}
mock_refusal_episodes = [
    mock_refusal_episode_third,
    mock_refusal_episode_first,
    mock_refusal_episode_second
]


def mock_get_refusal_episodes(*args, **kwargs):
    return mock_refusal_episodes
