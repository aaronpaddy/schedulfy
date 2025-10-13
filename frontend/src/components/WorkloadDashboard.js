import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
  Tooltip
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import api from '../services/api';

/**
 * Workload Visualization Dashboard
 * Shows predicted weekly workload, risk analysis, and recommendations
 */
function WorkloadDashboard({ courseIds }) {
  const [workloadData, setWorkloadData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (courseIds && courseIds.length > 0) {
      fetchWorkloadPrediction();
    }
  }, [courseIds]);

  const fetchWorkloadPrediction = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/ai/workload-prediction', {
        course_ids: courseIds
      });

      if (response.data.success) {
        setWorkloadData(response.data.prediction);
      } else {
        throw new Error('Failed to predict workload');
      }
    } catch (err) {
      console.error('Workload prediction error:', err);
      setError('Unable to predict workload. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!courseIds || courseIds.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          Add courses to your schedule to see workload predictions
        </Typography>
      </Paper>
    );
  }

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>
          Analyzing workload...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error">{error}</Alert>
    );
  }

  if (!workloadData) {
    return null;
  }

  // Prepare weekly forecast data for chart
  const weeklyData = workloadData.weekly_forecast?.map((hours, index) => ({
    week: `Week ${index + 1}`,
    hours: hours,
    isHeavy: hours > workloadData.total_hours_per_week * 1.2,
    isLight: hours < workloadData.total_hours_per_week * 0.8
  })) || [];

  // Course breakdown data for chart
  const courseBreakdown = workloadData.course_breakdown || [];

  // Risk level styling
  const getRiskColor = (level) => {
    switch (level) {
      case 'low': return 'success';
      case 'moderate': return 'info';
      case 'high': return 'warning';
      case 'very_high': return 'error';
      default: return 'default';
    }
  };

  const getRiskIcon = (level) => {
    switch (level) {
      case 'low': return <CheckCircleIcon />;
      case 'moderate': return <TrendingUpIcon />;
      case 'high':
      case 'very_high': return <WarningIcon />;
      default: return null;
    }
  };

  const totalHours = workloadData.total_hours_per_week || 0;
  const riskLevel = workloadData.risk_level || 'moderate';
  const riskMessage = workloadData.risk_message || '';

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        📊 Workload Analysis & Predictions
      </Typography>

      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Weekly Hours
              </Typography>
              <Typography variant="h3" component="div">
                {totalHours}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                hours per week (average)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Risk Level
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, my: 1 }}>
                {getRiskIcon(riskLevel)}
                <Chip 
                  label={riskLevel.replace('_', ' ').toUpperCase()} 
                  color={getRiskColor(riskLevel)}
                  icon={getRiskIcon(riskLevel)}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {riskMessage}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Busiest Week
              </Typography>
              <Typography variant="h3" component="div">
                {Math.max(...weeklyData.map(w => w.hours)).toFixed(1)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                hours (Week {workloadData.busiest_weeks?.[0] || '-'})
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Weekly Forecast Chart */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Weekly Workload Forecast
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis label={{ value: 'Hours/Week', angle: -90, position: 'insideLeft' }} />
                <RechartsTooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <Paper sx={{ p: 1 }}>
                          <Typography variant="body2">
                            {payload[0].payload.week}
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {payload[0].value} hours
                          </Typography>
                        </Paper>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="hours" fill="#8884d8">
                  {weeklyData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.isHeavy ? '#ff7043' : entry.isLight ? '#66bb6a' : '#42a5f5'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <Box sx={{ mt: 2, display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Box sx={{ width: 16, height: 16, bgcolor: '#66bb6a', borderRadius: 1 }} />
                <Typography variant="caption">Light</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Box sx={{ width: 16, height: 16, bgcolor: '#42a5f5', borderRadius: 1 }} />
                <Typography variant="caption">Normal</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Box sx={{ width: 16, height: 16, bgcolor: '#ff7043', borderRadius: 1 }} />
                <Typography variant="caption">Heavy</Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Course Breakdown */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Workload by Course
            </Typography>
            {courseBreakdown.map((item, index) => (
              <Box key={index} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">{item.course}</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {item.hours} hrs/week
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={(item.hours / totalHours) * 100}
                  sx={{ height: 8, borderRadius: 1 }}
                />
              </Box>
            ))}
          </Paper>
        </Grid>

        {/* Recommendations */}
        {riskLevel === 'high' || riskLevel === 'very_high' ? (
          <Grid item xs={12}>
            <Alert severity="warning" icon={<WarningIcon />}>
              <Typography variant="subtitle2" gutterBottom>
                ⚠️ Heavy Workload Detected
              </Typography>
              <Typography variant="body2">
                Your schedule shows {totalHours} hours/week which may be challenging. Consider:
              </Typography>
              <ul style={{ marginTop: 8, marginBottom: 0 }}>
                <li>Dropping one course to reduce stress</li>
                <li>Balancing with lighter electives</li>
                <li>Planning extra study time during weeks {workloadData.busiest_weeks?.join(', ')}</li>
              </ul>
            </Alert>
          </Grid>
        ) : riskLevel === 'low' ? (
          <Grid item xs={12}>
            <Alert severity="success" icon={<CheckCircleIcon />}>
              <Typography variant="body2">
                ✅ Your schedule looks balanced! You have capacity for {(25 - totalHours).toFixed(1)} more hours if you want to add another course.
              </Typography>
            </Alert>
          </Grid>
        ) : null}
      </Grid>
    </Box>
  );
}

export default WorkloadDashboard;

