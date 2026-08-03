## Testing launch_llmflux api

Have `prompts.jsonl` file in the diamond_dir for the endpoint

Use the below curl command to fetch the response from the api route
`tokens` is from the frontend cookies. From diamondhpc.ai, Inspect->applications->Cookies->tokens

```
curl -X POST "http://localhost:5328/api/launch_llmflux" \
 -H "Content-Type: application/json" \
 -b "tokens=<tokens-from-frontend>; primary_identity=<globus-primary-identity>" \
 -d '{
   "endpoint": "uuid-of-the-endpoint",
   "input_path": "prompts.jsonl",
   "output_path": "results.json",
   "model": "Qwen2.5-3B-Instruct",
   "batch_size": 4,
   "account": "bcqj-delta-gpu",
   "partition": "gpuA40x4",
   "task_name": "llmflux",
   "hf_token": ""
 }'
```
