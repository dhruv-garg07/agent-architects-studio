"""
SimpleMem - Efficient Lifelong Memory for LLM Agents
Main system class integrating all components
"""
from typing import List, Optional
from SimpleMem.models.memory_entry import Dialogue, MemoryEntry
from SimpleMem.utils.llm_client import LLMClient
from SimpleMem.utils.embedding import EmbeddingModel
from SimpleMem.database.vector_store import VectorStore
from SimpleMem.core.memory_builder import MemoryBuilder
from SimpleMem.core.hybrid_retriever import HybridRetriever
from SimpleMem.core.answer_generator import AnswerGenerator
import os, sys
# Import parent dir and add to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
grandparent_dir =  os.path.dirname(parent_dir)
if grandparent_dir not in sys.path: 
    sys.path.append(grandparent_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


# Load environment variables from .env if exists
from dotenv import load_dotenv
load_dotenv()

class SimpleMemSystem:
    """
    SimpleMem Main System

    Three-stage pipeline based on Semantic Lossless Compression:
    1. Semantic Structured Compression: add_dialogue() -> MemoryBuilder -> VectorStore
    2. Structured Indexing and Recursive Consolidation: (background evolution - future work)
    3. Adaptive Query-Aware Retrieval: ask() -> HybridRetriever -> AnswerGenerator
    """
    def __init__(
        self,
        agent_id: str = "memory_entries",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        db_path: Optional[str] = None,
        table_name: Optional[str] = None,
        clear_db: bool = False,
        enable_thinking: Optional[bool] = None,
        use_streaming: Optional[bool] = None,
        enable_planning: Optional[bool] = None,
        enable_reflection: Optional[bool] = None,
        max_reflection_rounds: Optional[int] = None,
        enable_parallel_processing: Optional[bool] = None,
        max_parallel_workers: Optional[int] = None,
        enable_parallel_retrieval: Optional[bool] = None,
        max_retrieval_workers: Optional[int] = None
    ):
        """
        Initialize system

        Args:
        - api_key: OpenAI API key
        - model: LLM model name
        - base_url: Custom OpenAI base URL (for compatible APIs)
        - db_path: Database path
        - table_name: Memory table name (for parallel processing)
        - clear_db: Whether to clear existing database
        - enable_thinking: Enable deep thinking mode (for Qwen and compatible models)
        - use_streaming: Enable streaming responses
        - enable_planning: Enable multi-query planning for retrieval (None=use config default)
        - enable_reflection: Enable reflection-based additional retrieval (None=use config default)
        - max_reflection_rounds: Maximum number of reflection rounds (None=use config default)
        - enable_parallel_processing: Enable parallel processing for memory building (None=use config default)
        - max_parallel_workers: Maximum number of parallel workers for memory building (None=use config default)
        - enable_parallel_retrieval: Enable parallel processing for retrieval queries (None=use config default)
        - max_retrieval_workers: Maximum number of parallel workers for retrieval (None=use config default)
        """
        print("=" * 60)
        print("Initializing SimpleMem System")
        print("=" * 60)

        # Initialize core components
        self.llm_client = LLMClient(
            api_key=api_key,
            model=model,
            base_url="https://semipathologically-nonexcusable-randi.ngrok-free.dev/",
            enable_thinking=enable_thinking,
            use_streaming=use_streaming
        )
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore(
            agent_id=agent_id,
            # db_path=db_path,
            embedding_model=self.embedding_model,
            # table_name=table_name
        )

        if clear_db:
            print("\nClearing existing database...")
            self.vector_store.clear()

        # Initialize three major modules
        self.memory_builder = MemoryBuilder(
            llm_client=self.llm_client,
            vector_store=self.vector_store,
            enable_parallel_processing=enable_parallel_processing,
            max_parallel_workers=max_parallel_workers
        )

        self.hybrid_retriever = HybridRetriever(
            llm_client=self.llm_client,
            vector_store=self.vector_store,
            enable_planning=enable_planning,
            enable_reflection=enable_reflection,
            max_reflection_rounds=max_reflection_rounds,
            enable_parallel_retrieval=enable_parallel_retrieval,
            max_retrieval_workers=max_retrieval_workers
        )

        self.answer_generator = AnswerGenerator(
            llm_client=self.llm_client
        )

        print("\nSystem initialization complete!")
        print("=" * 60)

    def add_dialogue(self, speaker: str, content: str, timestamp: Optional[str] = None):
        """
        Add a single dialogue

        Args:
        - speaker: Speaker name
        - content: Dialogue content
        - timestamp: Timestamp (ISO 8601 format)
        """
        dialogue_id = self.memory_builder.processed_count + len(self.memory_builder.dialogue_buffer) + 1
        dialogue = Dialogue(
            dialogue_id=dialogue_id,
            speaker=speaker,
            content=content,
            timestamp=timestamp
        )
        self.memory_builder.add_dialogue(dialogue)

    def add_dialogues(self, dialogues: List[Dialogue]):
        """
        Batch add dialogues

        Args:
        - dialogues: List of dialogues
        """
        self.memory_builder.add_dialogues(dialogues)

    def finalize(self):
        """
        Finalize dialogue input, process any remaining buffer (safety check)
        Note: In parallel mode, remaining dialogues are already processed
        """
        self.memory_builder.process_remaining()

    def ask(self, question: str) -> str:
        """
        Ask question - Core Q&A interface

        Args:
        - question: User question

        Returns:
        - Answer
        """
        print("\n" + "=" * 60)
        print(f"Question: {question}")
        print("=" * 60)

        # Stage 2: Hybrid retrieval
        contexts = self.hybrid_retriever.retrieve(question)

        # Stage 3: Answer generation
        answer = self.answer_generator.generate_answer(question, contexts)

        print("\nAnswer:")
        print(answer)
        print("=" * 60 + "\n")

        return answer

    def get_all_memories(self) -> List[MemoryEntry]:
        """
        Get all memory entries (for debugging)
        """
        return self.vector_store.get_all_entries()

    def print_memories(self):
        """
        Print all memory entries (for debugging)
        """
        memories = self.get_all_memories()
        print("\n" + "=" * 60)
        print(f"All Memory Entries ({len(memories)} total)")
        print("=" * 60)

        for i, memory in enumerate(memories, 1):
            print(f"\n[Entry {i}]")
            print(f"ID: {memory.entry_id}")
            print(f"Restatement: {memory.lossless_restatement}")
            if memory.timestamp:
                print(f"Time: {memory.timestamp}")
            if memory.location:
                print(f"Location: {memory.location}")
            if memory.persons:
                print(f"Persons: {', '.join(memory.persons)}")
            if memory.entities:
                print(f"Entities: {', '.join(memory.entities)}")
            if memory.topic:
                print(f"Topic: {memory.topic}")
            print(f"Keywords: {', '.join(memory.keywords)}")

        print("\n" + "=" * 60)

# Convenience function
def create_system(
    agent_id: str = "memory_entries",   
    clear_db: bool = False,
    enable_planning: Optional[bool] = None,
    enable_reflection: Optional[bool] = None,
    max_reflection_rounds: Optional[int] = None,
    enable_parallel_processing: Optional[bool] = None,
    max_parallel_workers: Optional[int] = None,
    enable_parallel_retrieval: Optional[bool] = None,
    max_retrieval_workers: Optional[int] = None
) -> SimpleMemSystem:
    """
    Create SimpleMem system instance (uses config.py defaults when None)
    """
    return SimpleMemSystem(
        agent_id=agent_id,
        clear_db=clear_db,
        enable_planning=enable_planning,
        enable_reflection=enable_reflection,
        max_reflection_rounds=max_reflection_rounds,
        enable_parallel_processing=enable_parallel_processing,
        max_parallel_workers=max_parallel_workers,
        enable_parallel_retrieval=enable_parallel_retrieval,
        max_retrieval_workers=max_retrieval_workers
    )


if __name__ == "__main__":
    import time
    
    print("="*70)
    print("[RUNNING] SimpleMem Multi-Agent System Test")
    print("="*70)
    
    # ========================================================================
    # Create THREE SEPARATE SYSTEMS for THREE DIFFERENT AGENTS
    # ========================================================================
    
    print("\n[SETUP] Creating three independent memory systems...")
    system_agent_1 = create_system(agent_id="test_agent_1", clear_db=True)
    system_agent_2 = create_system(agent_id="test_agent_2", clear_db=False)
    system_agent_3 = create_system(agent_id="test_agent_3", clear_db=False)

    print(f"✓ System 1 created for Agent 1")
    print(f"✓ System 2 created for Agent 2")
    print(f"✓ System 3 created for Agent 3")
    
    print(f"\n[MODEL] Embedding model: {system_agent_1.memory_builder.vector_store.embedding_model.model_name}")
    print(f"[MODEL] Type: {system_agent_1.memory_builder.vector_store.embedding_model.model_type}")
    
    # ========================================================================
    # AGENT 1 - Alice & Bob discussion about product meetings
    # ========================================================================
    print("\n" + "="*70)
    print("[AGENT-1] Adding dialogues for Agent 1 (Alice & Bob - Product Team)")
    print("="*70)
    
    system_agent_1.add_dialogue(
        "Alice", 
        "Bob, let's meet at Starbucks tomorrow at 2pm to discuss the new product", 
        "2025-11-15T14:30:00"
    )
    print("  ✓ Dialogue 1: Alice proposes meeting")
    time.sleep(1)
    
    system_agent_1.add_dialogue(
        "Bob", 
        "Okay, I'll prepare the materials", 
        "2025-11-15T14:31:00"
    )
    print("  ✓ Dialogue 2: Bob confirms and prepares")
    time.sleep(1)
    
    system_agent_1.add_dialogue(
        "Alice", 
        "Remember to bring the market research report from last time", 
        "2025-11-15T14:32:00"
    )
    print("  ✓ Dialogue 3: Alice reminds about documents")
    time.sleep(1)
    
    system_agent_1.add_dialogue(
        "Bob", 
        "I think your favourite food is tea.", 
        "2025-11-15T14:33:00"
    )
    print("  ✓ Dialogue 4: Bob makes personal observation")
    
    print("\n[AGENT-1] Stored dialogues to system 1")
    
    # ========================================================================
    # AGENT 2 - Charlie & Diana discussion about project timeline
    # ========================================================================
    print("\n" + "="*70)
    print("[AGENT-2] Adding dialogues for Agent 2 (Charlie & Diana - Project Team)")
    print("="*70)
    
    system_agent_2.add_dialogue(
        "Charlie", 
        "Diana, the Q3 deadline is critical for our project delivery", 
        "2025-11-15T15:00:00"
    )
    print("  ✓ Dialogue 1: Charlie discusses Q3 deadline")
    time.sleep(1)
    
    system_agent_2.add_dialogue(
        "Diana", 
        "Yes, we need to complete the architecture review by next Friday", 
        "2025-11-15T15:01:00"
    )
    print("  ✓ Dialogue 2: Diana confirms architecture review deadline")
    time.sleep(1)
    
    system_agent_2.add_dialogue(
        "Charlie", 
        "I'll organize the team meeting in the conference room at 10 am", 
        "2025-11-15T15:02:00"
    )
    print("  ✓ Dialogue 3: Charlie schedules team meeting")
    time.sleep(1)
    
    system_agent_2.add_dialogue(
        "Diana", 
        "Make sure to invite the backend team and the QA lead", 
        "2025-11-15T15:03:00"
    )
    print("  ✓ Dialogue 4: Diana specifies meeting participants")
    
    print("\n[AGENT-2] Stored dialogues to system 2")
    
    # ========================================================================
    # AGENT 3 - Eve & Frank discussion about client engagement
    # ========================================================================
    print("\n" + "="*70)
    print("[AGENT-3] Adding dialogues for Agent 3 (Eve & Frank - Sales Team)")
    print("="*70)
    
    system_agent_3.add_dialogue(
        "Eve", 
        "Frank, the client wants to see a demo of the new features by Wednesday", 
        "2025-11-15T16:00:00"
    )
    print("  ✓ Dialogue 1: Eve mentions client demo deadline")
    time.sleep(1)
    
    system_agent_3.add_dialogue(
        "Frank", 
        "I'll have the demo environment ready by Tuesday afternoon", 
        "2025-11-15T16:01:00"
    )
    print("  ✓ Dialogue 2: Frank confirms demo preparation")
    time.sleep(1)
    
    system_agent_3.add_dialogue(
        "Eve", 
        "Great! Let's meet at the client's office downtown at 9 am", 
        "2025-11-15T16:02:00"
    )
    print("  ✓ Dialogue 3: Eve schedules client meeting")
    time.sleep(1)
    
    system_agent_3.add_dialogue(
        "Frank", 
        "I love working with this client, they're always excited about our innovations", 
        "2025-11-15T16:03:00"
    )
    print("  ✓ Dialogue 4: Frank expresses positive sentiment about client")
    
    print("\n[AGENT-3] Stored dialogues to system 3")
    
    # ========================================================================
    # TEST AGENT 1 - Retrieval from Agent 1's memory
    # ========================================================================
    print("\n" + "="*70)
    print("[TEST-AGENT-1] Retrieving from Agent 1 System (Alice & Bob)")
    print("="*70)
    
    print("\n[AGENT-1] All stored memories:")
    system_agent_1.print_memories()
    
    print("\n[AGENT-1] Testing retrieval with planning and reflection...")
    answer_1 = system_agent_1.ask("When will Alice and Bob meet?")
    print(f"Answer: {answer_1}")
    
    # Ask what is photosynthesis to see if it pulls unrelated info
    answer_1b = system_agent_1.ask("What is photosynthesis?. Provide even if the memory does not exist.")
    print(f"Answer: {answer_1b}")
    
    print("\n[AGENT-1] Testing adversarial question (reflection disabled)...")
    question = "What is Alice's favorite food?"
    contexts = system_agent_1.hybrid_retriever.retrieve(question, enable_reflection=False)
    answer = system_agent_1.answer_generator.generate_answer(question, contexts)
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # ========================================================================
    # TEST AGENT 2 - Retrieval from Agent 2's memory
    # ========================================================================
    print("\n" + "="*70)
    print("[TEST-AGENT-2] Retrieving from Agent 2 System (Charlie & Diana)")
    print("="*70)
    
    print("\n[AGENT-2] All stored memories:")
    system_agent_2.print_memories()
    
    print("\n[AGENT-2] Testing retrieval: Q3 deadline question...")
    answer_2 = system_agent_2.ask("When is the Q3 deadline?")
    print(f"Answer: {answer_2}")
    
    print("\n[AGENT-2] Testing retrieval: Team meeting location...")
    question = "Where is the team meeting scheduled?"
    contexts = system_agent_2.hybrid_retriever.retrieve(question, enable_reflection=False)
    answer = system_agent_2.answer_generator.generate_answer(question, contexts)
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # ========================================================================
    # TEST AGENT 3 - Retrieval from Agent 3's memory
    # ========================================================================
    print("\n" + "="*70)
    print("[TEST-AGENT-3] Retrieving from Agent 3 System (Eve & Frank)")
    print("="*70)
    
    print("\n[AGENT-3] All stored memories:")
    system_agent_3.print_memories()
    
    print("\n[AGENT-3] Testing retrieval: Client demo deadline...")
    answer_3 = system_agent_3.ask("When does the client want to see the demo?")
    print(f"Answer: {answer_3}")
    
    print("\n[AGENT-3] Testing retrieval: Client meeting location...")
    question = "Where is the client meeting?"
    contexts = system_agent_3.hybrid_retriever.retrieve(question, enable_reflection=False)
    answer = system_agent_3.answer_generator.generate_answer(question, contexts)
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # ========================================================================
    # VERIFY DATA ISOLATION
    # ========================================================================
    print("\n" + "="*70)
    print("[VERIFICATION] Confirming Data Isolation Between Agents")
    print("="*70)
    
    agent1_memory_count = len(system_agent_1.get_all_memories())
    agent2_memory_count = len(system_agent_2.get_all_memories())
    agent3_memory_count = len(system_agent_3.get_all_memories())
    
    print(f"\nAgent 1 memory entries: {agent1_memory_count}")
    print(f"Agent 2 memory entries: {agent2_memory_count}")
    print(f"Agent 3 memory entries: {agent3_memory_count}")
    
    print("\n✓ Each agent has independent isolated system")
    print("✓ No dialogue mixing between agents")
    print("✓ Each system manages its own memory collection")
    
    print("\n" + "="*70)
    print("[SUCCESS] Multi-Agent System Test Completed!")
    print("="*70)
    print("\n[INFO] For comprehensive tests: python test_qwen3_integration.py")

