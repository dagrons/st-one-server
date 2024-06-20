from typing import Dict

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.chroma import Chroma

from app.core.config import setting
from app.schema import SearchKWArgs


def get_vectordb():
    embedding = HuggingFaceEmbeddings(model_name=setting.EMBEDDING_PATH)
    vector_store = Chroma.from_texts(
        ['张强强毕业于兰州大学，今年28岁，喜欢唱，跳，rap，篮球',
         '贺月辉毕业于北京邮电大学，今年25岁，喜欢羽毛球，电影，写代码',
         '代镜毕业于重庆大学，今年27岁，喜欢做饭，唱歌，睡觉',
         '张强强和贺月辉以及代镜目前在同一家单位就职，是非常好的朋友'],
        metadatas=[
            {'author': '张强强'},
            {'author': '贺月辉'},
            {'author': '代镜'},
            {'author': '贺月辉'}
        ],
        embedding=embedding
    )
    return vector_store


vector_store = get_vectordb()


def get_retriever():
    retriever = vector_store.as_retriever(search_type="similarity_score_threshold", search_kwargs={
        'k': 4,
        'score_threshold': -100.0
    })
    return retriever


retriever = get_retriever()

search_type_kwarg_map = {
    'similarity': ('k'),
    'similarity_score_threshold': ('score_threshold'),
    'mmr': ('k', 'score_threshold', 'fetch_k', 'lambda_mult')
}


async def _search(query: str, search_type: str, search_kwargs: SearchKWArgs, filter: Dict[str, str]):
    if search_type == "similarity":
        docs = await vector_store.asimilarity_search_with_score(query=query, **search_kwargs.model_dump(
            include=search_type_kwarg_map[search_type]), filter=filter)
        return [(doc[0].page_content, doc[1]) for doc in docs]
    elif search_type == "similarity_score_threshold":
        docs = await vector_store.asimilarity_search_with_relevance_scores(query=query, **search_kwargs.model_dump(
            include=search_type_kwarg_map[search_type]), filter=filter)
        return [(doc[0].page_content, doc[1]) for doc in docs]
    else:
        docs = await vector_store.amax_marginal_relevance_search(query=query, **search_kwargs.model_dump(
            include=search_type_kwarg_map[search_type]), filter=filter)
        return [doc.page_content for doc in docs]
