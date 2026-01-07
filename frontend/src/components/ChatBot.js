import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Trash2, User, Loader2, Minimize2, Maximize2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { toast } from './ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Custom Cartoon Rhino Icon Component
const RhinoIcon = ({ className = "h-6 w-6", color = "currentColor" }) => (
  <svg 
    viewBox="0 0 64 64" 
    className={className}
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Body */}
    <ellipse cx="36" cy="38" rx="20" ry="16" fill={color === "currentColor" ? "#6B7280" : color}/>
    {/* Head */}
    <circle cx="18" cy="32" r="14" fill={color === "currentColor" ? "#9CA3AF" : color}/>
    {/* Ear */}
    <ellipse cx="10" cy="22" rx="4" ry="6" fill={color === "currentColor" ? "#6B7280" : color}/>
    <ellipse cx="10" cy="22" rx="2" ry="4" fill="#F9A8D4"/>
    {/* Horn */}
    <path d="M8 28 L2 20 L6 18 L12 26 Z" fill="#E5E7EB"/>
    <path d="M12 30 L8 24 L10 22 L14 28 Z" fill="#D1D5DB"/>
    {/* Eye */}
    <circle cx="20" cy="30" r="4" fill="white"/>
    <circle cx="21" cy="30" r="2.5" fill="#1F2937"/>
    <circle cx="22" cy="29" r="1" fill="white"/>
    {/* Nose/Snout */}
    <ellipse cx="8" cy="36" rx="5" ry="4" fill={color === "currentColor" ? "#6B7280" : color}/>
    <circle cx="6" cy="35" r="1.5" fill="#1F2937"/>
    <circle cx="10" cy="35" r="1.5" fill="#1F2937"/>
    {/* Smile */}
    <path d="M14 40 Q18 44 22 40" stroke="#1F2937" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    {/* Legs */}
    <rect x="24" y="48" width="6" height="10" rx="3" fill={color === "currentColor" ? "#6B7280" : color}/>
    <rect x="36" y="48" width="6" height="10" rx="3" fill={color === "currentColor" ? "#6B7280" : color}/>
    <rect x="46" y="48" width="6" height="10" rx="3" fill={color === "currentColor" ? "#6B7280" : color}/>
    {/* Tail */}
    <path d="M56 38 Q62 36 60 42 Q58 46 54 44" stroke={color === "currentColor" ? "#6B7280" : color} strokeWidth="3" fill="none" strokeLinecap="round"/>
    {/* Spots/details */}
    <circle cx="30" cy="34" r="2" fill={color === "currentColor" ? "#9CA3AF" : "#D1D5DB"} opacity="0.5"/>
    <circle cx="42" cy="36" r="3" fill={color === "currentColor" ? "#9CA3AF" : "#D1D5DB"} opacity="0.5"/>
  </svg>
);

// Small Rhino for messages
const RhinoSmall = ({ className = "h-4 w-4" }) => (
  <span className={className} style={{ fontSize: '1rem', lineHeight: 1 }}>🦏</span>
);

const ChatBot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  // Load chat history when session exists
  useEffect(() => {
    if (sessionId && isOpen) {
      loadChatHistory();
    }
  }, [sessionId, isOpen]);

  const loadChatHistory = async () => {
    if (!sessionId) return;
    
    try {
      const response = await fetch(`${API}/chat-history/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
          const formattedMessages = data.messages.flatMap(msg => [
            { role: 'user', content: msg.user_message, timestamp: msg.timestamp },
            { role: 'assistant', content: msg.assistant_response, timestamp: msg.timestamp }
          ]);
          setMessages(formattedMessages);
        }
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date().toISOString() }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API}/chatbot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to get response');
      }

      const data = await response.json();
      
      // Save session ID for continuity
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      // Add assistant response to chat
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response,
        timestamp: new Date().toISOString()
      }]);

    } catch (error) {
      console.error('Chat error:', error);
      toast.error(error.message || 'Failed to send message');
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = async () => {
    if (sessionId) {
      try {
        await fetch(`${API}/chat-history/${sessionId}`, {
          method: 'DELETE'
        });
      } catch (error) {
        console.error('Error clearing chat history:', error);
      }
    }
    setMessages([]);
    setSessionId(null);
    toast.success('Chat cleared');
  };

  const toggleChat = () => {
    if (!isOpen) {
      setIsMinimized(false);
    }
    setIsOpen(!isOpen);
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  // Suggested questions for new users
  const suggestedQuestions = [
    "What's the total revenue?",
    "Which items sell the most?",
    "Show me profit by group",
    "What periods have data?"
  ];

  const askSuggestedQuestion = (question) => {
    setInputMessage(question);
    setTimeout(() => sendMessage(), 100);
  };

  // Floating chat button when closed
  if (!isOpen) {
    return (
      <button
        onClick={toggleChat}
        className="fixed bottom-20 right-6 z-50 w-14 h-14 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center group"
        title="Chat with AI Assistant"
      >
        <MessageCircle className="h-6 w-6 group-hover:scale-110 transition-transform" />
        <span className="absolute -top-2 -right-2 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-xs font-bold animate-pulse">
          AI
        </span>
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-20 right-6 z-50 transition-all duration-300 ${
        isMinimized ? 'w-72' : 'w-96'
      }`}
    >
      <Card className="shadow-2xl border-0 overflow-hidden">
        {/* Header */}
        <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bot className="h-5 w-5" />
              <CardTitle className="text-base font-semibold">AI Sales Assistant</CardTitle>
            </div>
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={clearChat}
                className="h-7 w-7 text-white/80 hover:text-white hover:bg-white/20"
                title="Clear chat"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMinimize}
                className="h-7 w-7 text-white/80 hover:text-white hover:bg-white/20"
                title={isMinimized ? "Maximize" : "Minimize"}
              >
                {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleChat}
                className="h-7 w-7 text-white/80 hover:text-white hover:bg-white/20"
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Chat Content */}
        {!isMinimized && (
          <CardContent className="p-0">
            {/* Messages Area */}
            <div className="h-80 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.length === 0 ? (
                <div className="text-center py-6">
                  <Bot className="h-12 w-12 mx-auto text-blue-500 mb-3" />
                  <p className="text-gray-600 text-sm mb-4">
                    Hi! I'm your AI assistant. Ask me anything about your sales data!
                  </p>
                  <div className="space-y-2">
                    <p className="text-xs text-gray-500 mb-2">Try asking:</p>
                    {suggestedQuestions.map((question, index) => (
                      <button
                        key={index}
                        onClick={() => askSuggestedQuestion(question)}
                        className="block w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white rounded-br-md'
                          : msg.isError
                          ? 'bg-red-100 text-red-800 rounded-bl-md'
                          : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md'
                      }`}
                    >
                      <div className="flex items-start space-x-2">
                        {msg.role === 'assistant' && (
                          <Bot className={`h-4 w-4 mt-0.5 flex-shrink-0 ${msg.isError ? 'text-red-500' : 'text-blue-500'}`} />
                        )}
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        {msg.role === 'user' && (
                          <User className="h-4 w-4 mt-0.5 flex-shrink-0 text-blue-200" />
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              
              {/* Loading indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-sm border border-gray-100">
                    <div className="flex items-center space-x-2">
                      <Bot className="h-4 w-4 text-blue-500" />
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-white border-t border-gray-200">
              <div className="flex items-center space-x-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about your sales data..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isLoading}
                />
                <Button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="h-10 w-10 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-gray-400 text-center mt-2">
                Powered by GPT-5.1 • Press Enter to send
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
};

export default ChatBot;
