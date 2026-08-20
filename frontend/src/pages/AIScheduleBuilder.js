import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Tab,
  Tabs,
  Button,
  Card,
  CardContent,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ChatIcon from '@mui/icons-material/Chat';
import BarChartIcon from '@mui/icons-material/BarChart';
import SchoolIcon from '@mui/icons-material/School';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';

// Import AI components
import AIChatBot from '../components/AIChatBot';
import AIRecommendations from '../components/AIRecommendations';
import WorkloadDashboard from '../components/WorkloadDashboard';
import api, { scheduleAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

/**
 * AI-Powered Schedule Builder - Main Page
 * Combines chat interface, recommendations, and workload analysis
 */
function AIScheduleBuilder() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scheduleId = searchParams.get('scheduleId');
  
  const [activeTab, setActiveTab] = useState(0);
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [scheduleData, setScheduleData] = useState(null);
  const [maxCredits, setMaxCredits] = useState(18);
  const [existingSchedule, setExistingSchedule] = useState(null);
  const [isAddingToSchedule, setIsAddingToSchedule] = useState(false);
  const [userSchedules, setUserSchedules] = useState([]);
  const [showSchedulePicker, setShowSchedulePicker] = useState(false);

  useEffect(() => {
    fetchCourses();
    if (user?.id) {
      fetchUserPreferences();
      fetchUserSchedules();
    }
    if (scheduleId) {
      fetchExistingSchedule(scheduleId);
    }
  }, [scheduleId, user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchCourses = async () => {
    try {
      const response = await api.get('/courses');
      setAllCourses(response.data.courses || []);
    } catch (error) {
      console.error('Error fetching courses:', error);
    }
  };

  const fetchUserPreferences = async () => {
    try {
      const userId = user?.id;
      if (!userId) return;

      // Try to get from backend first
      try {
        const response = await api.get(`/users/${userId}/preferences`);
        if (response.data && response.data.preferences) {
          const maxCreds = response.data.preferences.max_credits_per_semester || 18;
          setMaxCredits(maxCreds);
          // Save to localStorage for future
          localStorage.setItem(`user_preferences_${userId}`, JSON.stringify(response.data.preferences));
          return;
        }
      } catch (backendError) {
        console.log('Backend preferences not available, trying localStorage');
      }

      // Fallback to localStorage
      const storedPrefs = localStorage.getItem(`user_preferences_${userId}`);
      if (storedPrefs) {
        const prefs = JSON.parse(storedPrefs);
        setMaxCredits(prefs.max_credits_per_semester || 18);
      }
    } catch (error) {
      console.error('Error fetching user preferences:', error);
      setMaxCredits(18); // Default fallback
    }
  };

  const fetchUserSchedules = async () => {
    try {
      const response = await scheduleAPI.getUserSchedules();
      const schedules = response.data.schedules || response.data || [];
      console.log('📅 Fetched schedules:', schedules);
      console.log('📋 Schedule count:', schedules.length);
      console.log('🔍 scheduleId from URL:', scheduleId);
      setUserSchedules(schedules);
      
      // If user has schedules and not editing a specific one, show picker
      if (schedules.length > 0 && !scheduleId) {
        console.log('✅ Should show schedule picker!');
        setShowSchedulePicker(true);
      } else {
        console.log('❌ Not showing picker. Schedules:', schedules.length, 'scheduleId:', scheduleId);
      }
    } catch (error) {
      console.error('Error fetching user schedules:', error);
    }
  };

  const loadExistingScheduleById = async (id) => {
    setShowSchedulePicker(false);
    await fetchExistingSchedule(id);
  };

  const startNewSchedule = () => {
    setShowSchedulePicker(false);
    setExistingSchedule(null);
    setSelectedCourses([]);
    setIsAddingToSchedule(false);
  };

  const fetchExistingSchedule = async (id) => {
    try {
      setLoading(true);
      const response = await scheduleAPI.getSchedule(id);
      setExistingSchedule(response.data);
      setSelectedCourses(response.data.courses || []);
      setIsAddingToSchedule(true);
    } catch (error) {
      console.error('Error fetching existing schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCourse = (courseCode) => {
    // Find course by code
    const course = allCourses.find(c => c.code === courseCode);
    if (!course) {
      alert('Course not found!');
      return;
    }

    // Check if course is already selected
    if (selectedCourses.find(c => c.id === course.id)) {
      alert('This course is already in your schedule!');
      return;
    }

    // Check credit limit
    const currentCredits = selectedCourses.reduce((sum, c) => sum + c.credits, 0);
    const newTotalCredits = currentCredits + course.credits;
    
    if (newTotalCredits > maxCredits) {
      const shouldAdd = window.confirm(
        `⚠️ Credit Limit Warning!\n\n` +
        `Adding ${course.code} would exceed your credit limit:\n` +
        `Current: ${currentCredits} credits\n` +
        `Adding: ${course.credits} credits\n` +
        `New total: ${newTotalCredits} credits\n` +
        `Your limit: ${maxCredits} credits\n\n` +
        `This exceeds your limit by ${newTotalCredits - maxCredits} credits.\n\n` +
        `Do you want to add this course anyway?`
      );
      
      if (!shouldAdd) {
        return;
      }
    }

    // Check for time conflicts
    const hasConflict = checkTimeConflict(course, selectedCourses);
    if (hasConflict) {
      const shouldAdd = window.confirm(
        `⚠️ Time Conflict Warning!\n\n` +
        `${course.code} conflicts with an existing course in your schedule.\n\n` +
        `Do you want to add this course anyway?`
      );
      
      if (!shouldAdd) {
        return;
      }
    }

    // Add the course
    setSelectedCourses([...selectedCourses, course]);
  };

  const checkTimeConflict = (newCourse, existingCourses) => {
    if (!newCourse.time_slots || newCourse.time_slots.length === 0) {
      return false; // No time info, assume no conflict
    }

    for (const existingCourse of existingCourses) {
      if (!existingCourse.time_slots || existingCourse.time_slots.length === 0) {
        continue; // No time info, skip
      }

      // Check each time slot of the new course against each time slot of existing courses
      for (const newSlot of newCourse.time_slots) {
        for (const existingSlot of existingCourse.time_slots) {
          if (newSlot.day === existingSlot.day) {
            // Same day, check time overlap
            const newStart = timeToMinutes(newSlot.start_time);
            const newEnd = timeToMinutes(newSlot.end_time);
            const existingStart = timeToMinutes(existingSlot.start_time);
            const existingEnd = timeToMinutes(existingSlot.end_time);

            // Check for overlap
            if ((newStart < existingEnd) && (newEnd > existingStart)) {
              return true; // Conflict found
            }
          }
        }
      }
    }
    return false;
  };

  const timeToMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const [time, period] = timeStr.split(' ');
    const [hours, minutes] = time.split(':').map(Number);
    let totalMinutes = hours * 60 + minutes;
    if (period === 'PM' && hours !== 12) {
      totalMinutes += 12 * 60;
    } else if (period === 'AM' && hours === 12) {
      totalMinutes -= 12 * 60;
    }
    return totalMinutes;
  };

  const handleRemoveCourse = (courseId) => {
    setSelectedCourses(selectedCourses.filter(c => c.id !== courseId));
  };

  const handleGenerateSchedule = async () => {
    setLoading(true);
    try {
      const response = await api.post('/schedule/generate', {
        semester: 'Fall',
        year: 2025,
        max_credits: maxCredits,
        use_ai: true
      });

      if (response.data.schedule) {
        setScheduleData(response.data);
        setSelectedCourses(response.data.schedule.courses || []);
        setSaveDialogOpen(true);
      }
    } catch (error) {
      console.error('Error generating schedule:', error);
      alert('Failed to generate schedule. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    if (isAddingToSchedule && existingSchedule) {
      // Add courses to existing schedule
      try {
        setLoading(true);
        const courseIds = selectedCourses.map(c => c.id);
        await scheduleAPI.updateSchedule(existingSchedule.id, courseIds);
        setSaveDialogOpen(false);
        alert('Courses added to your schedule successfully!');
        navigate(`/schedule/${existingSchedule.id}`);
      } catch (error) {
        console.error('Error updating schedule:', error);
        alert(error.response?.data?.error || 'Failed to add courses. Please try again.');
      } finally {
        setLoading(false);
      }
    } else {
      // Create new schedule
      try {
        setLoading(true);
        const courseIds = selectedCourses.map(c => c.id);
        const response = await scheduleAPI.createSchedule({
          name: `Fall 2025 Schedule`,
          semester: 'Fall',
          year: 2025,
          course_ids: courseIds,
          max_credits: maxCredits
        });
        
        setSaveDialogOpen(false);
        alert('Schedule saved successfully!');
        navigate(`/schedule/${response.data.schedule.id}`);
      } catch (error) {
        console.error('Error creating schedule:', error);
        alert(error.response?.data?.error || 'Failed to save schedule. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const totalCredits = selectedCourses.reduce((sum, course) => sum + course.credits, 0);
  const selectedCourseIds = selectedCourses.map(c => c.id);

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {existingSchedule && (
              <Button
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate(`/schedule/${existingSchedule.id}`)}
                sx={{ mr: 2 }}
              >
                Back to Schedule
              </Button>
            )}
            <AutoAwesomeIcon sx={{ fontSize: 40 }} color="primary" />
            <Box>
              <Typography variant="h3" component="h1">
                {existingSchedule ? 'AI Course Suggestions' : 'AI Schedule Builder'}
              </Typography>
              <Typography variant="h6" color="text.secondary">
                {existingSchedule 
                  ? `Get AI-powered course suggestions for ${existingSchedule.name}`
                  : 'Build your perfect schedule with AI-powered recommendations, workload predictions, and natural language chat'
                }
              </Typography>
            </Box>
          </Box>
          
          {/* Save Schedule Button */}
          {selectedCourses.length > 0 && !existingSchedule && (
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => setSaveDialogOpen(true)}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 600,
                textTransform: 'none',
                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                  boxShadow: '0 6px 20px rgba(102, 126, 234, 0.4)',
                  transform: 'translateY(-1px)',
                },
                transition: 'all 0.2s ease',
              }}
            >
              Save Schedule ({totalCredits} credits)
            </Button>
          )}
        </Box>
      </Box>

      {/* Schedule Picker Dialog */}
      <Dialog 
        open={showSchedulePicker} 
        onClose={() => setShowSchedulePicker(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Choose an Option
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 3 }}>
            You have {userSchedules.length} existing schedule{userSchedules.length !== 1 ? 's' : ''}. 
            Would you like to continue working on one or create a new schedule?
          </Typography>

          <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
            Your Schedules:
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
            {userSchedules.map((schedule) => {
              const totalCredits = schedule.courses?.reduce((sum, c) => sum + (c.credits || 0), 0) || 0;
              return (
                <Card 
                  key={schedule.id}
                  sx={{ 
                    cursor: 'pointer',
                    border: '2px solid transparent',
                    '&:hover': {
                      borderColor: 'primary.main',
                      boxShadow: 2,
                    }
                  }}
                  onClick={() => loadExistingScheduleById(schedule.id)}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="h6">{schedule.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {schedule.courses?.length || 0} courses • {totalCredits} credits
                        </Typography>
                      </Box>
                      <Chip 
                        label="Continue" 
                        color="primary" 
                        icon={<ArrowBackIcon />}
                      />
                    </Box>
                  </CardContent>
                </Card>
              );
            })}
          </Box>

          <Button
            fullWidth
            variant="outlined"
            size="large"
            startIcon={<AddIcon />}
            onClick={startNewSchedule}
          >
            Start a Brand New Schedule
          </Button>
        </DialogContent>
      </Dialog>

      {/* Info Banner */}
      {existingSchedule ? (
        <Alert severity="success" sx={{ mb: 3 }} icon={<AutoAwesomeIcon />}>
          <strong>Context-Aware AI!</strong> The AI knows your current schedule ({selectedCourses.length} courses, {totalCredits} credits) 
          and will suggest courses that complement what you have, avoid conflicts, and fit within your {maxCredits}-credit limit.
          <br />
          <Typography variant="body2" sx={{ mt: 1 }}>
            💡 <strong>Tip:</strong> Add courses from the AI recommendations, then click <strong>"Save Changes to Schedule"</strong> to update your schedule.
          </Typography>
        </Alert>
      ) : (
        <Alert severity="info" sx={{ mb: 3 }} icon={<AutoAwesomeIcon />}>
          <strong>Building a New Schedule!</strong> Start from scratch with AI-powered recommendations. Your max credits per semester: <strong>{maxCredits} credits</strong>.
          <br />
          <Typography variant="body2" sx={{ mt: 1 }}>
            Use the chat or browse recommendations below to add courses, then save your schedule!
          </Typography>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Left Column - Selected Courses & Workload */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 3, bgcolor: 'primary.main', color: 'white' }}>
            <Typography variant="h6" gutterBottom>
              Your Schedule
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box>
                <Typography variant="h3">{selectedCourses.length}</Typography>
                <Typography variant="body2">Courses</Typography>
              </Box>
              <Box>
                <Typography variant="h3">{totalCredits} / {maxCredits}</Typography>
                <Typography variant="body2">Credits</Typography>
              </Box>
            </Box>
            <Button 
              variant="contained" 
              fullWidth 
              sx={{ mt: 2, bgcolor: 'white', color: 'primary.main' }}
              startIcon={<AutoAwesomeIcon />}
              onClick={handleGenerateSchedule}
              disabled={loading}
            >
              {loading ? 'Generating...' : 'AI Generate Schedule'}
            </Button>
            {isAddingToSchedule && selectedCourses.length > 0 && (
              <Button 
                variant="contained" 
                fullWidth 
                sx={{ 
                  mt: 1, 
                  bgcolor: 'rgba(255, 255, 255, 0.9)', 
                  color: 'success.main',
                  '&:hover': {
                    bgcolor: 'white',
                  }
                }}
                startIcon={<SaveIcon />}
                onClick={async () => {
                  try {
                    setLoading(true);
                    const courseIds = selectedCourses.map(c => c.id);
                    await scheduleAPI.updateSchedule(existingSchedule.id, courseIds);
                    alert('Schedule updated successfully!');
                    navigate(`/schedule/${existingSchedule.id}`);
                  } catch (error) {
                    console.error('Error updating schedule:', error);
                    alert(error.response?.data?.error || 'Failed to update schedule. Please try again.');
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save Changes to Schedule'}
              </Button>
            )}
          </Paper>

          {/* Selected Courses List */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Selected Courses
            </Typography>
            {selectedCourses.length === 0 ? (
              <Typography color="text.secondary" variant="body2">
                No courses selected yet. Use the AI assistant or recommendations to add courses.
              </Typography>
            ) : (
              <Box>
                {selectedCourses.map((course) => (
                  <Card key={course.id} sx={{ mb: 1 }}>
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle2">
                            {course.code}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {course.name}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'end', gap: 0.5 }}>
                          <Chip label={`${course.credits} cr`} size="small" />
                          <Button 
                            size="small" 
                            color="error"
                            onClick={() => handleRemoveCourse(course.id)}
                          >
                            Remove
                          </Button>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Right Column - AI Features */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ mb: 3 }}>
            <Tabs 
              value={activeTab} 
              onChange={(e, newValue) => setActiveTab(newValue)}
              variant="fullWidth"
            >
              <Tab icon={<ChatIcon />} label="AI Chat Assistant" />
              <Tab icon={<SchoolIcon />} label="AI Recommendations" />
              <Tab icon={<BarChartIcon />} label="Workload Analysis" />
            </Tabs>
          </Paper>

          {/* Tab Content */}
          <Box>
            {activeTab === 0 && (
              <AIChatBot 
                onCourseSuggested={handleAddCourse}
                currentSchedule={selectedCourses}
                scheduleContext={existingSchedule ? {
                  scheduleName: existingSchedule.name,
                  currentCredits: totalCredits,
                  maxCredits: maxCredits,
                  remainingCredits: maxCredits - totalCredits
                } : null}
              />
            )}
            
            {activeTab === 1 && (
              <AIRecommendations 
                onCourseAdd={handleAddCourse}
                targetCredits={maxCredits - totalCredits}
                scheduleId={existingSchedule?.id}
                isAddingToSchedule={isAddingToSchedule}
                currentSchedule={selectedCourses}
                maxCredits={maxCredits}
                allCourses={allCourses}
              />
            )}
            
            {activeTab === 2 && (
              selectedCourses.length > 0 ? (
                <WorkloadDashboard courseIds={selectedCourseIds} />
              ) : (
                <Paper sx={{ p: 4, textAlign: 'center' }}>
                  <BarChartIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    No Workload Data Yet
                  </Typography>
                  <Typography color="text.secondary">
                    Add courses to your schedule to see detailed workload analysis
                  </Typography>
                </Paper>
              )
            )}
          </Box>
        </Grid>
      </Grid>

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)}>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AutoAwesomeIcon color="primary" />
            AI Schedule Generated!
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="success" sx={{ mb: 2 }}>
            Successfully generated an AI-optimized schedule with {selectedCourses.length} courses
            ({totalCredits} credits).
          </Alert>
          
          {scheduleData?.workload_prediction && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Predicted Workload
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • {scheduleData.workload_prediction.total_hours_per_week} hours per week
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • Risk Level: {scheduleData.workload_prediction.risk_level}
              </Typography>
            </Box>
          )}

          {scheduleData?.conflicts_avoided && scheduleData.conflicts_avoided.length > 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                ✓ Time Conflicts Avoided: {scheduleData.conflicts_avoided.length}
              </Typography>
              <Typography variant="body2">
                The AI automatically detected and avoided courses with overlapping time slots:
              </Typography>
              {scheduleData.conflicts_avoided.map((conflict, idx) => (
                <Typography key={idx} variant="body2" sx={{ ml: 2, mt: 0.5 }}>
                  • {conflict.course} (conflicts with {conflict.conflicts_with})
                </Typography>
              ))}
            </Alert>
          )}

          {scheduleData?.ai_recommendations && scheduleData.ai_recommendations.length > 0 && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                AI Selected Courses:
              </Typography>
              {scheduleData.ai_recommendations.slice(0, 5).map((rec, idx) => (
                <Chip 
                  key={idx} 
                  label={rec.course_code} 
                  size="small" 
                  sx={{ mr: 1, mb: 1 }}
                />
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>
            Close
          </Button>
          <Button 
            variant="contained" 
            startIcon={<SaveIcon />}
            onClick={handleSaveSchedule}
          >
            Save Schedule
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default AIScheduleBuilder;

