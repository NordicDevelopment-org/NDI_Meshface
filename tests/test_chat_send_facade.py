from meshdash import chat_send as facade
from meshdash import chat_send_prepare as prepare_impl
from meshdash import chat_send_response as response_impl


def test_chat_send_facade_reexports_impl_symbols():
    assert facade.prepare_chat_send_input is prepare_impl.prepare_chat_send_input
    assert facade.delivery_state_for_send is response_impl.delivery_state_for_send
    assert facade.build_chat_send_response is response_impl.build_chat_send_response
