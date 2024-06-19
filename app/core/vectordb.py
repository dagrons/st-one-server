from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.chroma import Chroma

from app.core.config import setting


def get_vectordb():
    embedding = HuggingFaceEmbeddings(model_name=setting.EMBEDDING_PATH)
    vector_store = Chroma.from_texts(
        ['张强强毕业于兰州大学，今年28岁，喜欢唱，跳，rap，篮球',
         '贺月辉毕业于北京邮电大学，今年25岁，喜欢羽毛球，电影，写代码',
         '代镜毕业于重庆大学，今年27岁，喜欢做饭，唱歌，睡觉'],
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
