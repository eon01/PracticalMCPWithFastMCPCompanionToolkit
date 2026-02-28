# agent.py
import asyncio

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

load_dotenv()


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "pdf-reader": {
                "transport": "stdio",
                "command": "npx",
                "args": ["@sylphx/pdf-reader-mcp"],
            }
        }
    )
    tools = await client.get_tools()
    read_pdf = next(t for t in tools if t.name == "read_pdf")

    pdf_path = input("PDF path: ").strip()

    print("Reading PDF...")
    raw = await read_pdf.ainvoke(
        {"sources": [{"path": pdf_path}], "include_full_text": True}
    )
    full_text = raw if isinstance(raw, str) else str(raw)

    print("Indexing...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(full_text)
    index = FAISS.from_texts(chunks, OpenAIEmbeddings())
    print(f"Ready — {len(chunks)} chunks indexed.\n")

    llm = ChatOpenAI(model="gpt-5-mini")
    while True:
        question = input("You: ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        docs = index.similarity_search(question, k=5)
        context = "\n\n---\n\n".join(d.page_content for d in docs)

        answer = llm.invoke(
            f"Answer based only on the context below.\n\nContext:\n{context}\n\nQuestion: {question}"
        )
        print(f"Agent: {answer.content}\n")


if __name__ == "__main__":
    asyncio.run(main())
