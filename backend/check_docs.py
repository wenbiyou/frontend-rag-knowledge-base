from database import get_vector_store

vs = get_vector_store()
data = vs.collection.get(limit=1, include=['documents', 'metadatas'])
print('=== 文档内容示例 ===')
if data['documents']:
    print('文档内容前500字符:')
    print(data['documents'][0][:500] if data['documents'][0] else '空')
    print()
    print('=== 元数据 ===')
    print(data['metadatas'][0] if data['metadatas'] else '无元数据')
else:
    print('无文档')
