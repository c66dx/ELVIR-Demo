import asyncio
import unittest

from starlette.requests import Request
from starlette.responses import Response

from app.core.middleware import (
    get_request_metrics_snapshot,
    request_id_middleware,
    reset_request_metrics,
)


class HealthMetricsTestCase(unittest.TestCase):
    def _build_request(self, path: str):
        scope = {
            'type': 'http',
            'http_version': '1.1',
            'method': 'GET',
            'path': path,
            'raw_path': path.encode('utf-8'),
            'headers': [],
            'query_string': b'',
            'scheme': 'http',
            'server': ('testserver', 80),
            'client': ('127.0.0.1', 12345),
            'root_path': '',
        }

        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        return Request(scope, receive)

    def test_request_metrics_collect_status_buckets(self):
        reset_request_metrics()

        async def ok(_request):
            return Response(status_code=200)

        async def boom(_request):
            raise RuntimeError('boom')

        for _ in range(3):
            req = self._build_request('/ok')
            asyncio.run(request_id_middleware(req, ok))

        req_fail = self._build_request('/fail')
        with self.assertRaises(RuntimeError):
            asyncio.run(request_id_middleware(req_fail, boom))

        metrics = get_request_metrics_snapshot()
        self.assertEqual(metrics.get('requests_total'), 4)
        self.assertEqual(metrics.get('requests_by_status_bucket:2xx'), 3)
        self.assertEqual(metrics.get('requests_by_status_bucket:5xx'), 1)


if __name__ == '__main__':
    unittest.main()
