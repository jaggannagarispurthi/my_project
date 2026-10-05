import streamlit as st
import chromadb
import ollama

from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="University AI Chatbot",
    page_icon="🎓",
    layout="wide"
)


# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🎓 AI Chatbot for University Information Retrieval")

st.write(
    "Ask questions about courses, departments, admissions, "
    "fees, facilities, hostel, transport and other university information."
)


# --------------------------------------------------
# MODEL
# --------------------------------------------------

@st.cache_resource
def load_embedding_model():

    return SentenceTransformer(
        "all-MiniLM-L6-v2"
    )


model = load_embedding_model()


# --------------------------------------------------
# LOAD UNIVERSITY DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    with open(
        "data/university_info.txt",
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


text = load_data()


# --------------------------------------------------
# CREATE TEXT CHUNKS
# --------------------------------------------------

def create_chunks(
    text,
    chunk_size=500,
    overlap=100
):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap

    return chunks


chunks = create_chunks(text)


# --------------------------------------------------
# CHROMADB
# --------------------------------------------------

@st.cache_resource
def create_database():

    client = chromadb.PersistentClient(
        path="./chroma_db"
    )

    collection = client.get_or_create_collection(
        name="university_information"
    )

    # Add documents only if collection is empty

    if collection.count() == 0:

        embeddings = model.encode(
            chunks
        ).tolist()

        ids = [
            f"document_{i}"
            for i in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings
        )

    return collection


collection = create_database()


# --------------------------------------------------
# SEARCH FUNCTION
# --------------------------------------------------

def search_information(
    question,
    number_of_results=3
):

    query_embedding = model.encode(
        question
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=number_of_results
    )

    return results["documents"][0]


# --------------------------------------------------
# GENERATE ANSWER USING OLLAMA
# --------------------------------------------------

def generate_answer(
    question,
    context
):

    context_text = "\n\n".join(context)

    prompt = f"""
You are a university information assistant.

Answer the user's question using ONLY the information
provided in the context below.

Do not make up information.

If the answer is not available in the context,
say:

"Sorry, I could not find this information
in the university knowledge base."

Keep the answer clear and simple.

CONTEXT:
{context_text}

QUESTION:
{question}

ANSWER:
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("⚙️ Chat Settings")

if st.sidebar.button("Clear Chat"):

    st.session_state.messages = []

    st.rerun()


if st.sidebar.checkbox("Show University Data"):

    st.sidebar.text_area(
        "University Information",
        text,
        height=400
    )


# --------------------------------------------------
# CHAT HISTORY
# --------------------------------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# --------------------------------------------------
# USER QUESTION
# --------------------------------------------------

question = st.chat_input(
    "Ask your university-related question..."
)


if question:

    # Display user question

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)


    # Search relevant information

    relevant_information = search_information(
        question
    )


    # Generate AI answer

    answer = generate_answer(
        question,
        relevant_information
    )


    # Display answer

    with st.chat_message("assistant"):

        st.markdown(answer)


    # Store answer

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )