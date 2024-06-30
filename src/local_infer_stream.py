import requests
import json

url = "http://localhost:11434/api/generate"

# 设置请求参数
data = {
    "model": "codestral",
    "prompt": "write codes for using push gateway to collect metrics in python",
    "format": "json",
    "stream": True
}

# 发送 HTTP 请求
response = requests.post(url, json=data, stream=True)

output_token_idx = 0
for line in response.iter_lines():
    if line:
        response_content = line.decode("utf-8")
        output_token_idx += 1
        print(output_token_idx, response_content)
        #token = json.loads(response_content).get("response", None)
        #if token:
        #    print(token)

response.close()