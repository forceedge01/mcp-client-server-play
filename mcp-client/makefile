serve:
	uvicorn main:app --reload

test:
# 	query='How do I connect langchain and chromadb'
	curl "http://127.0.0.1:8000/query" -X POST -H "content-type: application/json" -d '{"query": "$(query)"}'

tools:
	curl "http://127.0.0.1:8000/tools"