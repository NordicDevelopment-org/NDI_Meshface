from meshdash import history_store_runtime as facade
from meshdash import history_store_runtime_impl as impl


def test_history_store_runtime_facade_reexports_impl_store():
    assert facade.HistoryStore is impl.HistoryStore
