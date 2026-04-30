Traceback (most recent call last):
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 394, in handle_async_request
    resp = await self._pool.handle_async_request(req)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 256, in handle_async_request
    raise exc from None
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 236, in handle_async_request
    response = await connection.handle_async_request(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        pool_request.request
        ^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 101, in handle_async_request
    raise exc
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 78, in handle_async_request
    stream = await self._connect(request)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 124, in _connect
    stream = await self._network_backend.connect_tcp(**kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_backends/auto.py", line 31, in connect_tcp
    return await self._backend.connect_tcp(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_backends/anyio.py", line 113, in connect_tcp
    with map_exceptions(exc_map):
         ~~~~~~~~~~~~~~^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectTimeout

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/request/_httpxrequest.py", line 279, in do_request
    res = await self._client.request(
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1540, in request
    return await self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1629, in send
    response = await self._send_handling_auth(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<4 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1657, in _send_handling_auth
    response = await self._send_handling_redirects(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1694, in _send_handling_redirects
    response = await self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1730, in _send_single_request
    response = await transport.handle_async_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 393, in handle_async_request
    with map_httpcore_exceptions():
         ~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectTimeout

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Users/noah/Desktop/raumzeit-ki-agent/src/bot.py", line 803, in <module>
    if __name__ == "__main__": main()
                               ~~~~^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/src/bot.py", line 800, in main
    try: asyncio.run(main_async())
         ~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 719, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/src/bot.py", line 776, in main_async
    await app.initialize(); await app.start(); await app.updater.start_polling()
    ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/ext/_application.py", line 489, in initialize
    await self.bot.initialize()
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/ext/_extbot.py", line 316, in initialize
    await super().initialize()
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/_bot.py", line 857, in initialize
    await self.get_me()
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/ext/_extbot.py", line 2008, in get_me
    return await super().get_me(
           ^^^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/_bot.py", line 990, in get_me
    result = await self._post(
             ^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/_bot.py", line 704, in _post
    return await self._do_post(
           ^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/ext/_extbot.py", line 370, in _do_post
    return await super()._do_post(
           ^^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/_bot.py", line 733, in _do_post
    result = await request.post(
             ^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/request/_baserequest.py", line 198, in post
    result = await self._request_wrapper(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<7 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/request/_baserequest.py", line 305, in _request_wrapper
    code, payload = await self.do_request(
                    ^^^^^^^^^^^^^^^^^^^^^^
    ...<7 lines>...
    )
    ^
  File "/Users/noah/Desktop/raumzeit-ki-agent/.venv/lib/python3.14/site-packages/telegram/request/_httpxrequest.py", line 296, in do_request
    raise TimedOut from err
telegram.error.TimedOut: Timed out
make: *** [run] Error 1
