import React, { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { formatIndianNumber } from "../utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api/customer`;

export default function CustomerBot() {
  const [activeTab, setActiveTab] = useState("chat"); // "chat" or "list"
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [sessionId, setSessionId] = useState("");
  
  // Chat States
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([
    {
      role: "assistant",
      content: "Hi! I'm Sandy. Need help finding something in-store or checking stock today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const chatEndRef = useRef(null);

  // List Checker States
  const [listInput, setListInput] = useState("");
  const [checkingList, setCheckingList] = useState(false);
  const [listResults, setListResults] = useState(null); // { available: [], unavailable: [] }
  const [checkedItems, setCheckedItems] = useState({}); // { item_name: boolean }
  const [itemQuantities, setItemQuantities] = useState({}); // { [item_name]: qty }
  const [showDisclaimer, setShowDisclaimer] = useState(() => {
    return !localStorage.getItem("sandy_disclaimer_dismissed");
  });

  // Generate Session ID on mount
  useEffect(() => {
    let sid = localStorage.getItem("sandy_customer_session_id");
    if (!sid) {
      sid = "cust_" + Math.random().toString(36).substring(2, 15);
      localStorage.setItem("sandy_customer_session_id", sid);
    }
    setSessionId(sid);
    fetchCategories();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (activeTab === "chat") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatHistory, activeTab]);

  // Rotates witty loading messages when chat is taking time
  useEffect(() => {
    let intervalId;
    if (chatLoading) {
      // Determine if this is the first search of the session (welcome message + first user message)
      const isFirstSearch = chatHistory.filter(m => m.role === 'user').length <= 1;
      
      const wittyMessages = isFirstSearch 
        ? [
            "Sandy is heading to the store shelves...",
            "Waking up the database... it stayed up late watching Rhino documentaries 🦏",
            "Checking the backroom... Sandy is scanning 4,660 product embeddings 🔍",
            "OpenAI is thinking... probably debating if tomatoes are a fruit or vegetable 🍅",
            "Still searching... Render's free tier container is having its morning coffee ☕",
            "Hang tight! Our server is doing stretch exercises before running your search 🏃‍♂️",
            "Sandy is currently checking the top shelves... (Rhinos aren't known for their height) 🪜",
            "Almost there! Double-checking the inventory records for you..."
          ]
        : [
            "Sandy is scanning the shelves...",
            "Double-checking the inventory list...",
            "OpenAI is running the numbers...",
            "Checking the storage room... almost got it!",
            "Sandy is consulting the store catalog..."
          ];

      setLoadingMessage(wittyMessages[0]);
      let index = 1;
      
      intervalId = setInterval(() => {
        if (index < wittyMessages.length) {
          setLoadingMessage(wittyMessages[index]);
          index++;
        }
      }, 3500); // Change message every 3.5 seconds
    } else {
      setLoadingMessage("");
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [chatLoading, chatHistory]);

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API}/categories`);
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || []);
      }
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  const handleAddProductFromChat = (prod) => {
    // Append "1 <Item Name>" to listInput text, each item on a new line
    setListInput((prev) => {
      const trimmed = prev.trim();
      const prefix = trimmed ? "\n" : "";
      return trimmed + prefix + `1 ${prod.item_name}`;
    });

    // Merge directly into listResults.available
    setListResults((prev) => {
      const currentAvailable = prev?.available || [];
      const currentUnavailable = prev?.unavailable || [];
      
      const exists = currentAvailable.some((item) => item.matched_item === prod.item_name);
      if (exists) {
        setItemQuantities((q) => ({
          ...q,
          [prod.item_name]: (q[prod.item_name] || 1) + 1
        }));
        toast.success(`Incremented quantity of ${prod.item_name} in shopping list.`);
        return prev;
      }

      setItemQuantities((q) => ({
        ...q,
        [prod.item_name]: 1
      }));

      const newAvailable = [
        ...currentAvailable,
        {
          original_query: prod.item_name,
          clean_query: prod.item_name,
          requested_qty: 1,
          matched_item: prod.item_name,
          stock: prod.stock,
          category: prod.category,
          alternatives: []
        }
      ];

      toast.success(`Added ${prod.item_name} to shopping list!`);

      return {
        ...prev,
        available: newAvailable,
        unavailable: currentUnavailable
      };
    });
  };

  const handleSendChatMessage = async (textToSend) => {
    const msg = textToSend || chatMessage;
    if (!msg.trim()) return;

    // Add user message to history
    const userMsg = {
      role: "user",
      content: msg,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setChatHistory((prev) => [...prev, userMsg]);
    if (!textToSend) setChatMessage("");
    setChatLoading(true);

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          session_id: sessionId,
          category_filter: selectedCategory || null
        })
      });

      if (response.ok) {
        const data = await response.json();
        setChatHistory((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.response,
            checkedItems: data.checked_items || [],
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);

        if (data.additions && data.additions.length > 0) {
          const additionLines = [];
          const newQuants = {};
          
          setListResults((prev) => {
            let currentAvailable = prev?.available ? [...prev.available] : [];
            let currentUnavailable = prev?.unavailable ? [...prev.unavailable] : [];
            
            data.additions.forEach((add) => {
              additionLines.push(`${add.requested_qty} ${add.matched_item}`);
              newQuants[add.matched_item] = add.requested_qty;
              
              if (add.available) {
                const existingIdx = currentAvailable.findIndex((item) => item.matched_item === add.matched_item);
                if (existingIdx > -1) {
                  currentAvailable[existingIdx] = {
                    ...currentAvailable[existingIdx],
                    requested_qty: add.requested_qty
                  };
                } else {
                  currentAvailable.push({
                    original_query: add.original_query,
                    clean_query: add.clean_query,
                    requested_qty: add.requested_qty,
                    matched_item: add.matched_item,
                    stock: add.stock,
                    category: add.category,
                    alternatives: []
                  });
                }
              } else {
                const existingIdx = currentUnavailable.findIndex((item) => item.matched_item === add.matched_item);
                if (existingIdx > -1) {
                  currentUnavailable[existingIdx] = {
                    ...currentUnavailable[existingIdx],
                    requested_qty: add.requested_qty
                  };
                } else {
                  currentUnavailable.push({
                    original_query: add.original_query,
                    clean_query: add.clean_query,
                    requested_qty: add.requested_qty,
                    reason: add.reason || "Out of Stock",
                    matched_item: add.matched_item,
                    category: add.category
                  });
                }
              }
            });
            
            return {
              available: currentAvailable,
              unavailable: currentUnavailable
            };
          });

          // Append additions to listInput
          if (additionLines.length > 0) {
            setListInput((prev) => {
              const trimmed = prev.trim();
              const prefix = trimmed ? "\n" : "";
              return trimmed + prefix + additionLines.join("\n");
            });
          }

          // Update itemQuantities
          setItemQuantities((prev) => ({
            ...prev,
            ...newQuants
          }));

          toast.success(`Added ${data.additions.length} item(s) to your shopping list!`);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to get chatbot response");
      }
    } catch (error) {
      console.error("Chat error:", error);
      toast.error(error.message || "Unable to reach Sandy. Please try again.");
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble processing that request. Please try again in a moment.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleCheckList = async () => {
    if (!listInput.trim()) {
      toast.error("Please enter at least one item in the list.");
      return;
    }

    setCheckingList(true);
    // Split items by newline or comma
    const items = listInput
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);

    try {
      const response = await fetch(`${API}/check-list`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items,
          category_filter: selectedCategory || null,
          session_id: sessionId
        })
      });

      if (response.ok) {
        const data = await response.json();
        setListResults(data);
        
        // Initialize itemQuantities from requested_qty
        const initialQuants = {};
        if (data.available) {
          data.available.forEach((item) => {
            initialQuants[item.matched_item] = item.requested_qty || 1;
          });
        }
        setItemQuantities((prev) => ({ ...prev, ...initialQuants }));

        // Reset checkbox state
        setCheckedItems({});
        toast.success("List checked successfully!");
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to check shopping list");
      }
    } catch (error) {
      console.error("List checker error:", error);
      toast.error(error.message || "Failed to check list availability.");
    } finally {
      setCheckingList(false);
    }
  };

  const toggleItemChecked = (itemName) => {
    setCheckedItems((prev) => ({
      ...prev,
      [itemName]: !prev[itemName]
    }));
  };

  const handleQuickQuestion = (question) => {
    handleSendChatMessage(question);
  };

  return (
    <div className="bg-[#f8f9ff] text-[#0b1c30] min-h-screen font-sans flex flex-col relative overflow-x-hidden select-none">
      
      {/* Local print and responsive styles */}
      <style>{`
        .glass-panel {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.4);
          box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
        }
        .user-bubble {
          background: linear-gradient(135deg, #712ae2 0%, #3525cd 100%);
          box-shadow: 0 4px 15px rgba(113, 42, 226, 0.3);
        }
        .rhino-shimmer {
          position: relative;
          overflow: hidden;
        }
        .rhino-shimmer::after {
          content: "";
          position: absolute;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: linear-gradient(to right, transparent, rgba(255,255,255,0.3), transparent);
          transform: rotate(30deg);
          animation: shimmer 4s infinite linear;
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%) rotate(30deg); }
          100% { transform: translateX(100%) rotate(30deg); }
        }
        .chat-scroll::-webkit-scrollbar {
          display: none;
        }
        .chat-scroll {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fadeInUp 0.4s ease-out forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fadeIn 0.25s ease-out forwards;
        }
        .animate-scale-in {
          animation: scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; color: black !important; }
          .print-only { display: block !important; }
          .glass-panel { 
            backdrop-filter: none !important; 
            border: 1px solid #ccc !important;
            box-shadow: none !important;
            background: white !important;
            color: black !important;
          }
        }
      `}</style>

      {/* Ambient Background Glows */}
      <div className="fixed inset-0 z-[-1] opacity-40 pointer-events-none no-print">
        <div className="absolute top-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-[#8a4cfc] blur-[120px]"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[#4f46e5] blur-[100px]"></div>
      </div>

      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 border-b border-white/20 bg-white/70 backdrop-blur-xl shadow-sm no-print">
        <div className="flex justify-between items-center px-5 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-[#3525cd]/20 p-0.5 overflow-hidden bg-white">
              <img 
                alt="Sandy" 
                className="w-full h-full object-cover rounded-full" 
                src="/sandy-rhino.png"
              />
            </div>
            <div>
              <h1 className="font-semibold text-xl bg-gradient-to-r from-[#3525cd] to-[#b6166f] bg-clip-text text-transparent" style={{ fontFamily: 'Outfit, sans-serif' }}>Sandy</h1>
              <p className="text-[10px] text-emerald-600 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Online & ready
              </p>
            </div>
          </div>
          
          <div className="relative">
            <button 
              onClick={() => setCategoryDropdownOpen(!categoryDropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/80 border border-[#4f46e5]/10 hover:bg-[#eff4ff] transition-all text-[#3525cd] font-medium text-xs shadow-sm"
            >
              <span className="material-symbols-outlined text-[18px]">category</span>
              <span>{selectedCategory || "All Categories"}</span>
              <span className="material-symbols-outlined text-[16px] transition-transform duration-200" style={{ transform: categoryDropdownOpen ? 'rotate(180deg)' : 'rotate(0)' }}>keyboard_arrow_down</span>
            </button>

            {categoryDropdownOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white/95 backdrop-blur-md rounded-xl shadow-xl border border-white/20 py-2 z-[60] max-h-72 overflow-y-auto">
                <button
                  onClick={() => {
                    setSelectedCategory("");
                    setCategoryDropdownOpen(false);
                  }}
                  className={`w-full text-left px-4 py-2 hover:bg-[#3525cd]/10 text-xs font-medium transition-colors ${!selectedCategory ? 'text-[#3525cd] bg-[#3525cd]/5' : 'text-slate-700'}`}
                >
                  All Categories
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => {
                      setSelectedCategory(cat);
                      setCategoryDropdownOpen(false);
                    }}
                    className={`w-full text-left px-4 py-2 hover:bg-[#3525cd]/10 text-xs font-medium transition-colors ${selectedCategory === cat ? 'text-[#3525cd] bg-[#3525cd]/5' : 'text-slate-700'}`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col pt-20 pb-28 max-w-2xl w-full mx-auto px-5 no-print">
        
        {activeTab === "chat" && (
          /* TAB 1: SANDY CHAT PANEL */
          <div className="flex-1 flex flex-col min-h-0 justify-between">
            
            {/* Scrollable messages container */}
            <div className="flex-1 overflow-y-auto py-4 chat-scroll flex flex-col gap-5 max-h-[calc(100vh-290px)]">
              {chatHistory.map((msg, index) => (
                <div 
                  key={index}
                  className={`flex gap-3 max-w-[85%] animate-fade-in-up ${msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden bg-white border border-[#3525cd]/10 self-end mb-2">
                      <img 
                        alt="Sandy" 
                        className="w-full h-full object-cover" 
                        src="/sandy-rhino.png"
                      />
                    </div>
                  )}
                  
                  <div className="flex flex-col gap-1 w-full">
                    <div className={`p-3.5 rounded-2xl ${msg.role === 'user' ? 'user-bubble rounded-br-none text-white' : 'glass-panel rounded-bl-none text-[#0b1c30]'}`}>
                      <p className="text-[14px] leading-relaxed whitespace-pre-line" style={{ fontFamily: 'Inter, sans-serif' }}>
                        {msg.content}
                      </p>
                    </div>

                    {msg.role === 'assistant' && msg.checkedItems && msg.checkedItems.length > 0 && (
                      <div className="flex flex-col gap-2 mt-2 w-full">
                        {msg.checkedItems.map((prod, pIdx) => (
                          <div 
                            key={pIdx}
                            className="glass-panel p-3 rounded-xl flex items-center justify-between border-[#eff4ff] bg-white/40 shadow-sm"
                          >
                            <div className="min-w-0 flex-1 mr-2">
                              <p className="text-xs font-semibold text-slate-800 truncate">{prod.item_name}</p>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className={`text-[9px] font-bold px-1.5 rounded-full ${prod.stock > 0 ? 'text-[#712ae2] bg-[#eaddff]/60' : 'text-red-500 bg-red-50'}`}>
                                  {prod.category}
                                </span>
                                <span className={`text-[9px] font-medium ${prod.stock > 0 ? 'text-slate-500' : 'text-red-400'}`}>
                                  {prod.stock > 0 ? `${formatIndianNumber(prod.stock)} in stock` : 'Out of stock'}
                                </span>
                              </div>
                            </div>
                            {prod.stock > 0 && (
                              <button
                                onClick={() => handleAddProductFromChat(prod)}
                                className="w-8 h-8 rounded-full bg-[#eff4ff] hover:bg-[#3525cd] hover:text-white text-[#3525cd] flex items-center justify-center active:scale-90 transition-all flex-shrink-0"
                                title="Add to shopping list"
                              >
                                <span className="material-symbols-outlined text-[18px] font-bold">add</span>
                              </button>
                            )}
                            {prod.stock <= 0 && (
                              <span className="text-[9px] font-bold px-2 py-1 bg-red-100 text-red-500 rounded-full flex-shrink-0">Out of stock</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <span className={`text-[10px] text-slate-500 opacity-75 ${msg.role === 'user' ? 'text-right mr-1' : 'ml-1'}`}>
                      {msg.role === 'user' ? 'You' : 'Sandy'} • {msg.timestamp}
                    </span>
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex gap-3 max-w-[85%] self-start animate-fade-in-up">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden bg-white border border-[#3525cd]/10 self-end mb-2">
                    <img 
                      alt="Sandy" 
                      className="w-full h-full object-cover" 
                      src="/sandy-rhino.png"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <div className="glass-panel px-4 py-3 rounded-2xl rounded-bl-none text-[#0b1c30] flex flex-col gap-2 items-start max-w-sm">
                      {loadingMessage && (
                        <p className="text-xs text-slate-700 italic animate-pulse leading-relaxed">
                          {loadingMessage}
                        </p>
                      )}
                      <div className="flex space-x-1.5 py-1">
                        <div className="w-2 h-2 bg-[#8a4cfc] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-[#712ae2] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-[#3525cd] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Bottom Actions and Inputs (pinned to bottom of chat area) */}
            <div className="mt-3">
              {/* Suggested Pills */}
              <div className="flex gap-2 overflow-x-auto pb-3.5 chat-scroll no-scrollbar">
                <button 
                  onClick={() => handleQuickQuestion("Do you have popcorn in stock?")}
                  className="flex-shrink-0 px-4 py-2 rounded-full glass-panel text-[#3525cd] text-xs font-semibold hover:bg-[#4f46e5] hover:text-white transition-all active:scale-95 border-[#3525cd]/20"
                >
                  🍿 Check popcorn
                </button>
                <button 
                  onClick={() => handleQuickQuestion("What pickles do you have available?")}
                  className="flex-shrink-0 px-4 py-2 rounded-full glass-panel text-[#3525cd] text-xs font-semibold hover:bg-[#4f46e5] hover:text-white transition-all active:scale-95 border-[#3525cd]/20"
                >
                  🫙 Pickles available?
                </button>
                <button 
                  onClick={() => handleQuickQuestion("Do you have Dove shampoo?")}
                  className="flex-shrink-0 px-4 py-2 rounded-full glass-panel text-[#3525cd] text-xs font-semibold hover:bg-[#4f46e5] hover:text-white transition-all active:scale-95 border-[#3525cd]/20"
                >
                  🧴 Dove Shampoo
                </button>
                <button 
                  onClick={() => handleQuickQuestion("Check stock for banana chips")}
                  className="flex-shrink-0 px-4 py-2 rounded-full glass-panel text-[#3525cd] text-xs font-semibold hover:bg-[#4f46e5] hover:text-white transition-all active:scale-95 border-[#3525cd]/20"
                >
                  🍌 Banana chips
                </button>
                <button 
                  onClick={() => handleQuickQuestion("Is Chandrika soap in stock?")}
                  className="flex-shrink-0 px-4 py-2 rounded-full glass-panel text-[#3525cd] text-xs font-semibold hover:bg-[#4f46e5] hover:text-white transition-all active:scale-95 border-[#3525cd]/20"
                >
                  🧼 Chandrika soap
                </button>
              </div>

              {/* Chat Input Field */}
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSendChatMessage(); }}
                className="relative flex items-center gap-2"
              >
                <div className="relative flex-1 group">
                  <input 
                    className="w-full h-14 pl-12 pr-4 rounded-full glass-panel border-[#c7c4d8] focus:border-[#712ae2] focus:ring-0 text-slate-800 transition-all text-[15px]" 
                    placeholder={selectedCategory ? `Search items in ${selectedCategory}...` : "Ask Sandy anything..."}
                    type="text"
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    disabled={chatLoading}
                  />
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3525cd] opacity-50">
                    <span className="material-symbols-outlined">auto_awesome</span>
                  </div>
                </div>
                <button 
                  type="submit" 
                  disabled={chatLoading}
                  className="w-14 h-14 rounded-full user-bubble text-white flex items-center justify-center active:scale-90 transition-transform disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[24px]">send</span>
                </button>
              </form>
            </div>

          </div>
        )}

        {activeTab === "list" && (
          /* TAB 2: SHOPPING LIST CHECKER PANEL */
          <div className="space-y-6">
            
            {/* Input textarea box */}
            <div className="glass-panel p-6 rounded-[24px] space-y-4">
              <label 
                className="font-semibold text-lg text-[#3525cd] block" 
                htmlFor="list-input"
                style={{ fontFamily: 'Outfit, sans-serif' }}
              >
                Your Shopping List
              </label>
              
              <textarea 
                className="w-full h-36 bg-white/30 border border-white/50 backdrop-blur-sm rounded-xl p-4 text-[#464555] focus:ring-2 focus:ring-[#3525cd] focus:outline-none transition-all placeholder:text-[#c7c4d8] font-sans text-sm" 
                id="list-input" 
                placeholder="Paste or type your grocery list here... (e.g., Milk, Eggs, Bread. Put each item on a new line or separate by commas)"
                value={listInput}
                onChange={(e) => setListInput(e.target.value)}
                disabled={checkingList}
              />

              <button 
                onClick={handleCheckList}
                disabled={checkingList || !listInput.trim()}
                className="rhino-shimmer active-scale w-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white font-semibold py-4 rounded-xl shadow-lg hover:shadow-xl transition-all flex justify-center items-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined">fact_check</span>
                <span>{checkingList ? "Sandy is checking..." : "Check Availability"}</span>
              </button>
            </div>

            {/* Checker results rendering */}
            {listResults && (
              <div className="space-y-6">
                
                {/* 1. Unavailable warning block */}
                {listResults.unavailable && listResults.unavailable.length > 0 && (
                  <div className="bg-[#ffdad6]/40 border border-[#ba1a1a]/20 backdrop-blur-md p-6 rounded-[24px] space-y-3">
                    <div className="flex items-center gap-2 text-[#93000a]">
                      <span className="material-symbols-outlined text-[#ba1a1a]">warning</span>
                      <h2 className="font-semibold text-lg" style={{ fontFamily: 'Outfit, sans-serif' }}>Unavailable Items</h2>
                    </div>
                    <ul className="space-y-2">
                      {listResults.unavailable.map((item, idx) => (
                        <li key={idx} className="flex items-center justify-between p-3 bg-white/20 rounded-lg">
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-slate-800">{item.original_query}</span>
                            {item.matched_item && (
                              <span className="text-[11px] text-[#464555]">Matched: {item.matched_item}</span>
                            )}
                          </div>
                          <span className="text-xs font-semibold px-2.5 py-1 bg-[#ba1a1a] text-white rounded-full">
                            {item.reason}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 2. Available checklist items */}
                {listResults.available && listResults.available.length > 0 && (
                  <div className="space-y-3">
                    <h2 className="font-semibold text-lg text-slate-800 flex items-center gap-2 px-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                      <span className="material-symbols-outlined text-indigo-600">check_circle</span>
                      <span>Ready for Pickup</span>
                    </h2>
                    
                    <div className="space-y-2.5">
                      {listResults.available.map((item, idx) => {
                        const isChecked = !!checkedItems[item.matched_item];
                        const qty = itemQuantities[item.matched_item] || 1;
                        return (
                          <div 
                            key={idx} 
                            onClick={() => toggleItemChecked(item.matched_item)}
                            className="glass-panel p-4 rounded-xl flex items-center justify-between group hover:border-[#3525cd]/30 transition-all cursor-pointer select-none"
                            style={{ 
                              opacity: isChecked ? 0.6 : 1, 
                              transform: isChecked ? 'scale(0.98)' : 'scale(1)',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            {/* Left Side: Checkbox, Name, Category */}
                            <div className="flex items-center gap-3.5 flex-1 min-w-0">
                              <div className="relative flex items-center flex-shrink-0">
                                <input 
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => {}} // Click handled by parent div
                                  className="w-6 h-6 rounded border-[#c7c4d8] text-[#712ae2] focus:ring-[#712ae2] transition-all cursor-pointer"
                                />
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className={`font-semibold text-[15px] text-slate-800 truncate ${isChecked ? 'line-through text-slate-500' : ''}`}>
                                  {item.matched_item}
                                </p>
                                <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                                  <span className="text-[10px] font-bold text-[#712ae2] bg-[#eaddff]/60 px-2 py-0.5 rounded-full flex-shrink-0">
                                    {item.category}
                                  </span>
                                  {item.original_query !== item.matched_item && (
                                    <span className="text-[10px] text-slate-500 truncate">
                                      for "{item.original_query}"
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Right Side: Stepper and Stock Label */}
                            <div className="flex flex-col items-end gap-2 ml-4 flex-shrink-0">
                              {/* Stepper Controls */}
                              <div 
                                className="flex items-center bg-white/80 border border-[#4f46e5]/10 rounded-full p-0.5 shadow-sm"
                                onClick={(e) => e.stopPropagation()} // Stop propagation from parent div
                              >
                                <button
                                  onClick={() => {
                                    if (qty > 1) {
                                      setItemQuantities((prev) => ({
                                        ...prev,
                                        [item.matched_item]: qty - 1
                                      }));
                                    }
                                  }}
                                  disabled={qty <= 1}
                                  className="w-7 h-7 rounded-full flex items-center justify-center text-[#712ae2] hover:bg-[#eff4ff] disabled:opacity-30 disabled:hover:bg-transparent transition-colors font-bold text-lg select-none"
                                >
                                  -
                                </button>
                                <span className="w-8 text-center text-xs font-semibold text-slate-700 select-none">
                                  {qty}
                                </span>
                                <button
                                  onClick={() => {
                                    if (qty < item.stock) {
                                      setItemQuantities((prev) => ({
                                        ...prev,
                                        [item.matched_item]: qty + 1
                                      }));
                                    }
                                  }}
                                  disabled={qty >= item.stock}
                                  className="w-7 h-7 rounded-full flex items-center justify-center text-[#712ae2] hover:bg-[#eff4ff] disabled:opacity-30 disabled:hover:bg-transparent transition-colors font-bold text-lg select-none"
                                >
                                  +
                                </button>
                              </div>
                              
                              {/* Stock Label */}
                              <span className="block font-semibold text-[11px] text-[#464555] bg-white/60 border border-slate-100 rounded-md px-2 py-0.5 shadow-sm">
                                {formatIndianNumber(item.stock)} in stock
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 3. Action print buttons */}
                {(listResults.available?.length > 0 || listResults.unavailable?.length > 0) && (
                  <div className="pt-2">
                    <button 
                      onClick={() => window.print()}
                      className="active-scale w-full glass-panel py-4 rounded-xl border-[#712ae2]/20 flex items-center justify-center gap-2.5 hover:bg-white transition-all group font-semibold text-[#712ae2] shadow-sm hover:shadow"
                    >
                      <span className="material-symbols-outlined text-[#712ae2] transition-transform group-hover:-translate-y-0.5">print</span>
                      <span>Print & Save List</span>
                    </button>
                  </div>
                )}

              </div>
            )}

          </div>
        )}

        {activeTab === "help" && (
          /* TAB 3: HELP & FLOWCHART PANEL */
          <div className="space-y-6 animate-fade-in-up">
            <div className="glass-panel p-6 rounded-[24px] space-y-4 text-center">
              <h2 className="font-semibold text-2xl text-[#3525cd]" style={{ fontFamily: 'Outfit, sans-serif' }}>
                How to Shop with Sandy
              </h2>
              <p className="text-slate-600 text-sm max-w-md mx-auto">
                Sandy is your virtual grocery assistant. Follow these simple steps to check stock and build your store shopping list.
              </p>
            </div>

            {/* Vertical Flowchart Timeline */}
            <div className="relative border-l-2 border-dashed border-[#8a4cfc]/30 pl-8 ml-4 mr-2 space-y-8 py-4">
              
              {/* Step 1 */}
              <div className="relative">
                <div className="absolute -left-[43px] top-1.5 w-7 h-7 rounded-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white flex items-center justify-center text-xs font-bold shadow-[0_0_10px_rgba(138,76,252,0.4)]">
                  1
                </div>
                <div className="glass-panel p-6 rounded-2xl space-y-2 hover:translate-y-[-2px] transition-transform duration-300 border border-white/40">
                  <div className="flex items-center gap-2 text-[#712ae2]">
                    <span className="material-symbols-outlined font-bold">chat_bubble</span>
                    <h3 className="font-bold text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>Step 1: Ask Sandy (Chat)</h3>
                  </div>
                  <p className="text-slate-600 text-xs leading-relaxed">
                    Query stock in natural language or filter by category. Sandy understands normal queries like <em>"Do you have cookies?"</em> or <em>"Is whiskey in stock?"</em>. Narrow down searches using the dropdown filter at the top.
                  </p>
                  
                  {/* Visual Aid */}
                  <div className="mt-3 bg-white/40 rounded-xl p-3 border border-white/20 text-xs text-slate-600 flex flex-col gap-1.5 shadow-sm">
                    <div className="self-end bg-gradient-to-r from-[#712ae2] to-[#3525cd] text-white px-3 py-1.5 rounded-xl rounded-tr-none max-w-[85%] font-medium">
                      "Do you have Dove shampoo in stock?"
                    </div>
                    <div className="self-start bg-white/70 text-slate-800 px-3 py-1.5 rounded-xl rounded-tl-none border border-slate-100 max-w-[85%] font-medium shadow-[0_2px_5px_rgba(0,0,0,0.02)] flex gap-1.5 items-center">
                      <span>🧴 Dove Shampoo: <strong>5 in stock</strong></span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="relative">
                <div className="absolute -left-[43px] top-1.5 w-7 h-7 rounded-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white flex items-center justify-center text-xs font-bold shadow-[0_0_10px_rgba(138,76,252,0.4)]">
                  2
                </div>
                <div className="glass-panel p-6 rounded-2xl space-y-2 hover:translate-y-[-2px] transition-transform duration-300 border border-white/40">
                  <div className="flex items-center gap-2 text-[#712ae2]">
                    <span className="material-symbols-outlined font-bold">add_circle</span>
                    <h3 className="font-bold text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>Step 2: Add to Shopping List</h3>
                  </div>
                  <p className="text-slate-600 text-xs leading-relaxed">
                    When Sandy finds matching items, click the <strong>+</strong> button on any item card to instantly add it to your shopping list, or ask Sandy to add items directly in the chat window.
                  </p>

                  {/* Visual Aid */}
                  <div className="mt-3 bg-white/40 rounded-xl p-3 border border-white/20 text-xs text-slate-600 flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🧴</span>
                      <div>
                        <p className="font-semibold text-slate-800 text-[11px]">Dove Shampoo (180ml)</p>
                        <p className="text-[9px] text-slate-500 font-medium">Group I - 5 in stock</p>
                      </div>
                    </div>
                    <div className="w-7 h-7 rounded-full bg-[#eff4ff] text-[#3525cd] flex items-center justify-center font-bold shadow-sm">
                      <span className="material-symbols-outlined text-[16px] font-bold">add</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 3 */}
              <div className="relative">
                <div className="absolute -left-[43px] top-1.5 w-7 h-7 rounded-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white flex items-center justify-center text-xs font-bold shadow-[0_0_10px_rgba(138,76,252,0.4)]">
                  3
                </div>
                <div className="glass-panel p-6 rounded-2xl space-y-2 hover:translate-y-[-2px] transition-transform duration-300 border border-white/40">
                  <div className="flex items-center gap-2 text-[#712ae2]">
                    <span className="material-symbols-outlined font-bold">fact_check</span>
                    <h3 className="font-bold text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>Step 3: Check & Adjust List</h3>
                  </div>
                  <p className="text-slate-600 text-xs leading-relaxed">
                    Switch to the <strong>List Checker</strong> tab to paste or edit your shopping list. Check real-time stock levels of your entire list simultaneously and adjust purchase quantities with steppers.
                  </p>

                  {/* Visual Aid */}
                  <div className="mt-3 bg-white/40 rounded-xl p-3 border border-white/20 text-xs text-slate-600 flex flex-col gap-2 shadow-sm">
                    <div className="flex justify-between items-center bg-emerald-500/10 text-emerald-700 p-2 rounded-lg border border-emerald-500/10">
                      <span className="font-semibold flex items-center gap-1.5"><span className="material-symbols-outlined text-[15px]">check_circle</span> Dove Shampoo</span>
                      <div className="flex items-center gap-1.5">
                        <span className="bg-white/80 px-2 py-0.5 rounded text-[9px] text-slate-700 font-bold border border-slate-100">Qty: 2</span>
                        <span className="font-bold text-[9px]">In Stock</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 4 */}
              <div className="relative">
                <div className="absolute -left-[43px] top-1.5 w-7 h-7 rounded-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white flex items-center justify-center text-xs font-bold shadow-[0_0_10px_rgba(138,76,252,0.4)]">
                  4
                </div>
                <div className="glass-panel p-6 rounded-2xl space-y-2 hover:translate-y-[-2px] transition-transform duration-300 border border-white/40">
                  <div className="flex items-center gap-2 text-[#712ae2]">
                    <span className="material-symbols-outlined font-bold">print</span>
                    <h3 className="font-bold text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>Step 4: Check Off & Shop</h3>
                  </div>
                  <p className="text-slate-600 text-xs leading-relaxed">
                    As you collect items in the aisles, check them off digitally, or click <strong>Print & Save List</strong> to print a cleanly formatted receipt-slip to bring with you to checkout!
                  </p>

                  {/* Visual Aid */}
                  <div className="mt-3 bg-white/40 rounded-xl p-2.5 border border-white/20 text-center text-[#712ae2] font-semibold text-xs flex items-center justify-center gap-1.5 shadow-sm">
                    <span className="material-symbols-outlined text-[15px] font-bold">print</span> Print & Save List
                  </div>
                </div>
              </div>

            </div>

            {/* Quick Action Button to go to Chat */}
            <div className="pt-2 text-center">
              <button 
                onClick={() => setActiveTab("chat")}
                className="rhino-shimmer active-scale px-8 py-3.5 bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] text-white font-bold rounded-xl shadow-lg hover:shadow-xl transition-all inline-flex items-center gap-2"
              >
                <span className="material-symbols-outlined">rocket_launch</span>
                <span>Get Started Now</span>
              </button>
            </div>
          </div>
        )}

      </div>

      {/* Sticky Bottom Navigation Bar */}
      <nav className="fixed bottom-4 left-4 right-4 rounded-full z-50 border border-white/30 backdrop-blur-[30px] bg-white/20 shadow-xl max-w-md mx-auto no-print">
        <div className="flex justify-around items-center h-16 w-full p-2">
          {/* Tab 1 button */}
          <button 
            onClick={() => setActiveTab("chat")}
            className={`flex-1 flex flex-col items-center justify-center py-2 transition-all duration-200 ease-out rounded-full ${activeTab === 'chat' ? 'bg-[#8a4cfc] text-white shadow-[0_0_15px_rgba(138,76,252,0.4)]' : 'text-slate-600 opacity-70 hover:opacity-100'}`}
          >
            <span className="material-symbols-outlined" style={{ fontVariationSettings: activeTab === 'chat' ? "'FILL' 1" : "'FILL' 0" }}>chat_bubble</span>
            <span className="font-semibold text-[10px] mt-0.5">Chat</span>
          </button>
          
          {/* Tab 2 button */}
          <button 
            onClick={() => setActiveTab("list")}
            className={`flex-1 flex flex-col items-center justify-center py-2 transition-all duration-200 ease-out rounded-full ${activeTab === 'list' ? 'bg-[#8a4cfc] text-white shadow-[0_0_15px_rgba(138,76,252,0.4)]' : 'text-slate-600 opacity-70 hover:opacity-100'}`}
          >
            <span className="material-symbols-outlined" style={{ fontVariationSettings: activeTab === 'list' ? "'FILL' 1" : "'FILL' 0" }}>fact_check</span>
            <span className="font-semibold text-[10px] mt-0.5">List Checker</span>
          </button>

          {/* Tab 3 button */}
          <button 
            onClick={() => setActiveTab("help")}
            className={`flex-1 flex flex-col items-center justify-center py-2 transition-all duration-200 ease-out rounded-full ${activeTab === 'help' ? 'bg-[#8a4cfc] text-white shadow-[0_0_15px_rgba(138,76,252,0.4)]' : 'text-slate-600 opacity-70 hover:opacity-100'}`}
          >
            <span className="material-symbols-outlined" style={{ fontVariationSettings: activeTab === 'help' ? "'FILL' 1" : "'FILL' 0" }}>help_outline</span>
            <span className="font-semibold text-[10px] mt-0.5">Help</span>
          </button>
        </div>
      </nav>

      {/* PRINT-ONLY VIEW (HIDDEN ON SCREEN) */}
      {listResults && (
        <div className="hidden print-only p-10 bg-white text-black min-h-screen">
          <div className="border-b-2 border-slate-200 pb-4 mb-6">
            <h1 className="text-3xl font-bold text-slate-800">Sandy - Your Shopping List</h1>
            <p className="text-xs text-slate-500 mt-1">Generated on {new Date().toLocaleDateString()} at {new Date().toLocaleTimeString()}</p>
          </div>

          {/* Print: Available list */}
          {listResults.available && listResults.available.length > 0 && (
            <div className="mb-8">
              <h2 className="text-xl font-bold text-slate-700 mb-3 flex items-center gap-2">✓ Available Items (Pick Up In Store)</h2>
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                    <th className="py-2">Item Name</th>
                    <th className="py-2">Department</th>
                    <th className="py-2 text-center">Qty</th>
                    <th className="py-2 text-right">In Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {listResults.available.map((item, idx) => (
                    <tr key={idx} className="border-b border-slate-100 text-sm text-slate-700">
                      <td className="py-3 font-medium">
                        {item.matched_item}
                        {item.original_query !== item.matched_item && (
                          <span className="text-[11px] font-normal text-slate-400 block">Matches: "{item.original_query}"</span>
                        )}
                      </td>
                      <td className="py-3">{item.category}</td>
                      <td className="py-3 text-center font-semibold">{itemQuantities[item.matched_item] || item.requested_qty || 1}</td>
                      <td className="py-3 text-right font-medium">{formatIndianNumber(item.stock)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Print: Out of stock / not found list */}
          {listResults.unavailable && listResults.unavailable.length > 0 && (
            <div className="mb-8">
              <h2 className="text-xl font-bold text-red-600 mb-3">✕ Unavailable Items (Find Elsewhere)</h2>
              <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-600">
                {listResults.unavailable.map((item, idx) => (
                  <li key={idx}>
                    <span className="font-semibold text-slate-800">{item.original_query}</span>
                    {item.matched_item && <span className="text-slate-400"> (Matched: {item.matched_item})</span>}
                    <span className="text-red-500 font-bold ml-2">[{item.reason}]</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-16 text-center border-t border-slate-200 pt-4 text-xs text-slate-400">
            <p>Thank you for shopping with us! Assisted by Sandy the Grocery Concierge.</p>
          </div>
        </div>
      )}

      {/* Disclaimer Modal */}
      {showDisclaimer && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in no-print">
          <div className="glass-panel max-w-md w-full rounded-[28px] p-6 md:p-8 space-y-6 border border-white/30 shadow-2xl relative overflow-hidden animate-scale-in">
            {/* Ambient inner glow */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#8a4cfc] rounded-full blur-2xl opacity-40 pointer-events-none"></div>
            <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-[#3525cd] rounded-full blur-2xl opacity-30 pointer-events-none"></div>
            
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-[#eff4ff] text-[#3525cd] flex items-center justify-center shadow-inner">
                <span className="material-symbols-outlined text-[32px] font-bold">info</span>
              </div>
              <h3 className="font-bold text-xl text-slate-800" style={{ fontFamily: 'Outfit, sans-serif' }}>
                AI Stock Assistant Disclaimer
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed" style={{ fontFamily: 'Inter, sans-serif' }}>
                This application uses Artificial Intelligence to match products and check real-time stock positions. While we strive for accuracy, AI predictions may occasionally vary, and items shown in stock may not always be available.
                <br /><br />
                Please bear with us in case of non-availability.
              </p>
            </div>
            
            <button
              onClick={() => {
                localStorage.setItem("sandy_disclaimer_dismissed", "true");
                setShowDisclaimer(false);
              }}
              className="rhino-shimmer active-scale w-full bg-gradient-to-r from-[#8a4cfc] to-[#712ae2] hover:from-[#712ae2] hover:to-[#3525cd] text-white font-bold py-3.5 rounded-xl shadow-lg hover:shadow-xl transition-all text-sm flex justify-center items-center gap-2"
            >
              <span>I Understand</span>
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
