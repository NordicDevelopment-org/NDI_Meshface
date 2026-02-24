from meshdash import dashboard_runner as facade
from meshdash import dashboard_runner_impl as impl


def test_dashboard_runner_facade_reexports_impl_runtime():
    assert facade.run_dashboard_runtime is impl.run_dashboard_runtime
