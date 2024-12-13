import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode("utf-8"))

        # Extract parameters from the request
        endpoint = data["endpoint"]
        container_id = data["container_id"]
        task = data["task"]

        # Call the SDK function
        # result = sdk_single_node_task(endpoint, container_id, task)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "message": "Single node task executed successfully",
            # "result": result
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))
