import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Button,
  Divider
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';

/**
 * AI-Powered Chat Assistant for Schedule Building
 * Natural language interface for course recommendations
 */
function AIChatBot({ onCourseSuggested, currentSchedule = null, scheduleContext = null }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: (currentSchedule && currentSchedule.length > 0)
        ? `👋 Hi! I can see you're working on your schedule with ${currentSchedule.length} course${currentSchedule.length !== 1 ? 's' : ''} already selected.\n\n` +
          'I can help you:\n' +
          '- Find courses that complement what you have\n' +
          '- Check for time conflicts\n' +
          '- Balance your workload\n' +
          '- Suggest courses for your remaining credits\n\n' +
          'What would you like help with?'
        : '👋 Hi! I\'m your AI course advisor. I can help you build the perfect schedule!\n\n' +
          'Try asking me things like:\n' +
          '- "I need 15 credits, no Friday classes, focus on machine learning"\n' +
          '- "What courses should I take for software engineering?"\n' +
          '- "Suggest courses that aren\'t too heavy"\n' +
          '- "What goes well with CS225?"'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestedCourses, setSuggestedCourses] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const requestBody = {
        message: userMessage,
        include_history: true
      };
      
      // Include current schedule context if available
      if (currentSchedule && currentSchedule.length > 0) {
        requestBody.current_schedule = currentSchedule.map(course => ({
          code: course.code,
          name: course.name,
          credits: course.credits,
          time_slots: course.time_slots
        }));
      }
      
      if (scheduleContext) {
        requestBody.schedule_context = scheduleContext;
      }
      
      const response = await api.post('/ai/chat', requestBody);

      if (response.data.success) {
        // Add AI response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.data.message
        }]);

        // Update suggested courses
        if (response.data.suggested_courses && response.data.suggested_courses.length > 0) {
          setSuggestedCourses(response.data.suggested_courses);
        }
      } else {
        throw new Error(response.data.message || 'Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Sorry, I\'m having trouble connecting right now. Please try again in a moment.\n\n' +
                 'Make sure the OpenAI API key is configured in your backend .env file.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCourseClick = (courseCode) => {
    if (onCourseSuggested) {
      onCourseSuggested(courseCode);
    }
  };

  const quickPrompts = [
    '15 credits, no Friday classes',
    'Focus on machine learning',
    'Light workload semester',
    'Software engineering path'
  ];

  const handleQuickPrompt = (prompt) => {
    setInput(prompt);
  };

  return (
    <Paper elevation={3} sx={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ 
        p: 2, 
        bgcolor: 'primary.main', 
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        gap: 1
      }}>
        <SmartToyIcon />
        <Typography variant="h6">
          AI Schedule Assistant
        </Typography>
        <Chip 
          label="Powered by GPT-4" 
          size="small" 
          sx={{ ml: 'auto', bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
        />
      </Box>

      {/* Messages */}
      <Box sx={{ 
        flex: 1, 
        overflow: 'auto', 
        p: 2,
        bgcolor: '#f5f5f5'
      }}>
        {messages.map((message, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              mb: 2
            }}
          >
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'flex-start',
              maxWidth: '80%',
              gap: 1,
              flexDirection: message.role === 'user' ? 'row-reverse' : 'row'
            }}>
              {/* Avatar */}
              <Box sx={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                flexShrink: 0
              }}>
                {message.role === 'user' ? <PersonIcon /> : <SmartToyIcon />}
              </Box>

              {/* Message bubble */}
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  bgcolor: message.role === 'user' ? 'primary.main' : 'white',
                  color: message.role === 'user' ? 'white' : 'text.primary',
                  borderRadius: 2
                }}
              >
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </Paper>
            </Box>
          </Box>
        ))}
        
        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Box sx={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              bgcolor: 'secondary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white'
            }}>
              <SmartToyIcon />
            </Box>
            <Paper elevation={1} sx={{ p: 2 }}>
              <CircularProgress size={20} /> Thinking...
            </Paper>
          </Box>
        )}
        
        <div ref={messagesEndRef} />
      </Box>

      {/* Suggested Courses */}
      {suggestedCourses.length > 0 && (
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', bgcolor: '#f9f9f9' }}>
          <Typography variant="subtitle2" gutterBottom>
            💡 Suggested Courses:
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {suggestedCourses.map((code) => (
              <Chip
                key={code}
                label={code}
                color="primary"
                variant="outlined"
                onClick={() => handleCourseClick(code)}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Quick Prompts */}
      {messages.length === 1 && (
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" gutterBottom display="block">
            Quick start:
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {quickPrompts.map((prompt, idx) => (
              <Chip
                key={idx}
                label={prompt}
                size="small"
                onClick={() => handleQuickPrompt(prompt)}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Input */}
      <Divider />
      <Box sx={{ p: 2, display: 'flex', gap: 1, bgcolor: 'white' }}>
        <TextField
          fullWidth
          multiline
          maxRows={3}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask me anything about courses and scheduling..."
          variant="outlined"
          size="small"
          disabled={loading}
        />
        <IconButton 
          color="primary" 
          onClick={handleSend}
          disabled={!input.trim() || loading}
          sx={{ 
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' },
            '&:disabled': { bgcolor: 'grey.300' }
          }}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Paper>
  );
}

export default AIChatBot;

