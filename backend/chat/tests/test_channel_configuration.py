from tablechat.settings import base


def test_channel_layer_disables_socket_timeout_for_blocking_receive():
    host = base.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
    assert host["address"] == base.REDIS_URL
    assert host["socket_timeout"] is None
    assert host["socket_connect_timeout"] == 5
    assert host["socket_keepalive"] is True
    assert base.CHANNEL_LAYERS["default"]["CONFIG"]["group_expiry"] == 600
