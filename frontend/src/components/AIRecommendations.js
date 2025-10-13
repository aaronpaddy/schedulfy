import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Grid,
  LinearProgress,
  Alert,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Rating
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';
import SchoolIcon from '@mui/icons-material/School';
import AddIcon from '@mui/icons-material/Add';
import api from '../services/api';

/**
 * AI-Powered Course Recommendations
 * Shows personalized course suggestions with reasoning and career alignment
 */
function AIRecommendations({ onCourseAdd, targetCredits = 15, semester = 'Fall', year = 2025, scheduleId = null, isAddingToSchedule = false }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scheduleContext, setScheduleContext] = useState(null);

  useEffect(() => {
    fetchRecommendations();
  }, [semester, year, scheduleId]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);

    try {
      let response;
      
      // Use context-aware endpoint if adding to existing schedule
      if (scheduleId && isAddingToSchedule) {
        response = await api.post(`/ai/suggest-for-schedule/${scheduleId}`, {
          num_suggestions: 8
        });
        
        if (response.data.success) {
          setRecommendations(response.data.recommendations || []);
          setScheduleContext({
            currentCredits: response.data.current_credits,
            maxCredits: response.data.max_credits,
            remainingCredits: response.data.remaining_credits,
            scheduleName: response.data.schedule_name,
            context: response.data.context
          });
        } else {
          throw new Error('Failed to get schedule-specific recommendations');
        }
      } else {
        // Regular recommendations
        response = await api.post('/ai/recommendations', {
          target_credits: targetCredits,
          semester,
          year
        });

        if (response.data.success) {
          setRecommendations(response.data.recommendations || []);
        } else {
          throw new Error('Failed to get recommendations');
        }
      }
    } catch (err) {
      console.error('Recommendation error:', err);
      setError('Unable to get AI recommendations. Make sure OpenAI API key is configured.');
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyColor = (difficulty) => {
    if (difficulty <= 2) return 'success';
    if (difficulty <= 3.5) return 'info';
    if (difficulty <= 4) return 'warning';
    return 'error';
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <AutoAwesomeIcon color="primary" />
          <Typography variant="h6">
            AI is analyzing your profile...
          </Typography>
        </Box>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2 }} color="text.secondary">
          Considering your major, completed courses, career goals, and academic performance...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="warning">
        {error}
        <Button size="small" onClick={fetchRecommendations} sx={{ mt: 1 }}>
          Retry
        </Button>
      </Alert>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <AutoAwesomeIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          No recommendations yet
        </Typography>
        <Typography color="text.secondary">
          Complete your profile to get personalized course recommendations
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <AutoAwesomeIcon color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h5">
          AI-Powered Recommendations
        </Typography>
        <Chip 
          label={`${recommendations.length} courses`} 
          size="small" 
          color="primary" 
          sx={{ ml: 1 }}
        />
      </Box>

      {scheduleContext ? (
        <Alert severity="success" sx={{ mb: 3 }} icon={<AutoAwesomeIcon />}>
          <Typography variant="subtitle2" gutterBottom>
            {scheduleContext.context}
          </Typography>
          <Typography variant="body2">
            Current: {scheduleContext.currentCredits} credits • Available: {scheduleContext.remainingCredits} credits • Limit: {scheduleContext.maxCredits} credits
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            These suggestions are tailored to complement your existing courses and avoid time conflicts.
          </Typography>
        </Alert>
      ) : (
        <Alert severity="info" sx={{ mb: 3 }} icon={<AutoAwesomeIcon />}>
          These recommendations are personalized based on your major, completed courses, career goals, and learning preferences.
        </Alert>
      )}

      <Grid container spacing={2}>
        {recommendations.map((rec, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card 
              elevation={3}
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 6
                }
              }}
            >
              <CardContent sx={{ flex: 1 }}>
                {/* Course Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                  <Box>
                    <Typography variant="h6" component="div">
                      {rec.course_code}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {rec.course_name}
                    </Typography>
                  </Box>
                  <Chip 
                    label={rec.priority || 'Medium'}
                    color={getPriorityColor(rec.priority)}
                    size="small"
                  />
                </Box>

                {/* Conflict Warning */}
                {rec.has_conflict && rec.conflict_warning && (
                  <Alert severity="warning" sx={{ mb: 2, py: 0.5 }}>
                    <Typography variant="caption">
                      ⚠️ {rec.conflict_warning}
                    </Typography>
                  </Alert>
                )}

                {/* Badges */}
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                  <Chip 
                    icon={<TrendingUpIcon />}
                    label={`Difficulty: ${rec.difficulty || 3}/5`}
                    size="small"
                    color={getDifficultyColor(rec.difficulty || 3)}
                    variant="outlined"
                  />
                  <Chip 
                    icon={<WorkOutlineIcon />}
                    label={`${rec.estimated_workload || 10} hrs/week`}
                    size="small"
                    variant="outlined"
                  />
                  {rec.prerequisites_met !== undefined && (
                    <Chip 
                      label={rec.prerequisites_met ? '✓ Prerequisites Met' : '⚠️ Missing Prereqs'}
                      size="small"
                      color={rec.prerequisites_met ? 'success' : 'warning'}
                      variant="outlined"
                    />
                  )}
                </Box>

                <Divider sx={{ my: 2 }} />

                {/* Reasoning */}
                <Accordion defaultExpanded={index === 0}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle2">
                      💡 Why This Course?
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {rec.reasoning}
                    </Typography>
                  </AccordionDetails>
                </Accordion>

                {/* Career Relevance */}
                {rec.career_relevance && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle2">
                        🎯 Career Relevance
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary">
                        {rec.career_relevance}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}
              </CardContent>

              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button 
                  variant="contained" 
                  fullWidth
                  startIcon={<AddIcon />}
                  onClick={() => onCourseAdd && onCourseAdd(rec.course_code)}
                >
                  Add to Schedule
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Button 
          variant="outlined" 
          onClick={fetchRecommendations}
          startIcon={<AutoAwesomeIcon />}
        >
          Refresh Recommendations
        </Button>
      </Box>
    </Box>
  );
}

export default AIRecommendations;

