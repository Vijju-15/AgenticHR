"""Test suite for agents."""

import pytest
from src.agents.conversational_rag import ConversationalRAG
from src.agents.agentic_rag import AgenticRAG


class TestConversationalRAG:
    """Test conversational RAG agent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return ConversationalRAG()
    
    def test_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent is not None
        assert agent.llm is not None
        assert agent.retriever is not None
    
    def test_simple_query(self, agent):
        """Test simple information query."""
        response = agent.query("How many casual leaves are available per year?")
        
        assert "answer" in response
        assert response["answer"] is not None
        assert isinstance(response["answer"], str)
    
    def test_metrics(self, agent):
        """Test metrics tracking."""
        agent.query("Test query")
        metrics = agent.get_metrics()
        
        assert metrics["total_queries"] > 0
        assert "success_rate" in metrics


class TestAgenticRAG:
    """Test agentic RAG agent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return AgenticRAG()
    
    def test_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent is not None
        assert agent.llm is not None
        assert agent.retriever is not None
        assert len(agent.tools) > 0
    
    def test_information_query(self, agent):
        """Test information retrieval."""
        response = agent.query("What is the leave policy?")
        
        assert "answer" in response
        assert response["answer"] is not None
    
    def test_tool_query(self, agent):
        """Test query that should use tools."""
        response = agent.query(
            "Check leave balance for employee EMP123",
            context={"employee_id": "EMP123"}
        )
        
        assert "answer" in response
        # Should use check_leave_balance tool
        # assert "tools_used" in response
    
    def test_metrics(self, agent):
        """Test metrics tracking."""
        agent.query("Test query")
        metrics = agent.get_metrics()
        
        assert metrics["total_queries"] > 0
        assert "tool_calls" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
