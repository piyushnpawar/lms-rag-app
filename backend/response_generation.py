from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from ingestion import QDRANT_INSTANCE
import logging, asyncio
from cache import add_qa_entry

logger = logging.getLogger(__name__)

load_dotenv()

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        max_tokens=250)
except Exception as e:
    logging.error(f"Failed to initialize Gemini: {e}")
    exit()

async def generate_sub_queries(user_question: str) -> list[str]:
    logging.info("Generating sub-queries...")
    sub_query_prompt = f"""
    You are a query generation expert. Your task is to take a single user question about an insurance policy and break it down into 3 highly specific and effective search queries. These queries should be designed to retrieve the most relevant information from a technical document.

    User Question: {user_question}

    Provide your queries as a comma-separated list, without any extra text or numbering.
    For example: "grace period for premium payment, due date for premium, policy renewal grace period"
    """

    try:
        completion = await llm.ainvoke(sub_query_prompt)
        response_text = completion.content
        sub_queries = [q.strip() for q in response_text.split(',') if q.strip()]
        logging.info(f"Generated sub-queries: {sub_queries}")
        return sub_queries
    except Exception as e:
        logging.error(f"Error generating sub-queries: {e}")
        return [user_question]

async def retrieve_and_synthesize_context(queries: list[str]) -> str:
    full_context = ""
    unique_contexts = set()

    logging.info(f"Retrieving context for {len(queries)} queries...")
    for query in queries:
        try:
            results = await QDRANT_INSTANCE.asimilarity_search(query, k=3)
            for doc in results:
                unique_contexts.add(doc.page_content)
        except Exception as e:
            logging.error(f"Error during retrieval for query '{query}': {e}")
            
    try:
        full_context = "\n\n---\n\n".join(list(unique_contexts))
        logging.info("Context retrieval and synthesis complete.")
    except Exception as e:
        logging.error(f"Error during context synthesis: {e}")
        full_context = "Error synthesizing context."

    return full_context

async def answer_question_with_context(question: str, context: str) -> str:
    logging.info("Generating final answer...")
    final_prompt = f"""
    <|begin_of_text|>
    <|start_header_id|>system<|end_header_id|>
    You are an expert insurance policy document assistant. Provide a concise and accurate answer to the user's question based ONLY on the provided context.
    - Start with 'Yes' or 'No' if it is a direct yes/no question.
    - Extract all specific numbers, percentages, and conditions directly from the text.
    - If the answer is descriptive, provide a brief, well-structured summary.
    - If the context does not contain the answer, state that the information is not available in the document.

    Context:
    {context}
    <|eot_id|>

    <|start_header_id|>user<|end_header_id|>
    Question: {question}
    <|eot_id|>

    <|start_header_id|>assistant<|end_header_id|>
    """
    
    try:
        llm_with_limited_tokens = llm.with_config({"configurable": {"max_output_tokens": 50}})
        completion = await llm_with_limited_tokens.ainvoke(final_prompt)
        answer = completion.content.strip()
        logging.info("Final answer generated successfully.")
        return answer
    except Exception as e:
        logging.error(f"Error generating final answer with the LLM: {e}")
        return "An error occurred while trying to answer the question."

async def full_rag_pipeline(question) -> str:
    sub_queries = await generate_sub_queries(question)
    context = await retrieve_and_synthesize_context(sub_queries)
    answer = await answer_question_with_context(question, context)
    return answer

async def process_question(i,q):
    print(f"\nQuestion {i+1}: {q}")
    if q == "Cached":
        return "Cached"
    response = await full_rag_pipeline(q)
    print(f"Answer: {response}")
    print("-----------------------------------")
    return response
    
async def generateResponse(questions) -> list:
    print("\n--- Starting RAG Query Process ---")
    
    tasks = [process_question(i,q) for i,q in enumerate(questions)]
    answers = await asyncio.gather(*tasks)
    
    db_entry = [add_qa_entry(q,a) for i,(q,a) in enumerate(zip(questions,answers))]
    check = await asyncio.gather(*db_entry)
    
    failed = [i for i, result in enumerate(check) if result is None]
    if failed:
        logging.error(f"Failed to insert entries at indexes: {failed}")
    else:
        print("--- RAG Query Process Complete ---")
        return answers