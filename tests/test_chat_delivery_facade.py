from meshdash import chat_delivery as facade
from meshdash import chat_delivery_extract as extract_impl
from meshdash import chat_delivery_state as state_impl
from meshdash import chat_delivery_timeout as timeout_impl


def test_chat_delivery_facade_reexports_impl_symbols():
    assert facade.chat_message_id is state_impl.chat_message_id
    assert facade.set_delivery_state is state_impl.set_delivery_state
    assert facade.extract_routing_delivery_update is extract_impl.extract_routing_delivery_update
    assert facade.expire_pending_deliveries is timeout_impl.expire_pending_deliveries
