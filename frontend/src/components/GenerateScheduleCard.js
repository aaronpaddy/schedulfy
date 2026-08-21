import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Alert,
  Chip,
  TextField,
  Stack,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { AutoAwesome as AutoAwesomeIcon } from '@mui/icons-material';
import api, { scheduleAPI } from '../services/api';

/**
 * Generate a schedule in one click, wherever it is dropped.
 *
 * The generation logic lives on the server; this only collects the credit
 * limit, shows what came back, and saves. It reports what was held back and
 * why, so a short schedule explains itself rather than looking broken.
 */
const GenerateScheduleCard = ({ semester = 'Fall', year = 2025 }) => {
  const navigate = useNavigate();
  const [maxCredits, setMaxCredits] = useState(15);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [scheduleName, setScheduleName] = useState(`${semester} ${year} Schedule`);

  const courses = result?.schedule?.courses || [];

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.post('/schedule/generate', {
        semester,
        year,
        max_credits: maxCredits,
        use_ai: true,
      });
      setResult(response.data);
      if (!response.data?.schedule?.courses?.length) {
        setError(
          'No courses could be scheduled. Check your degree plan — everything ' +
            'may be completed, or waiting on prerequisites.'
        );
      }
    } catch (err) {
      setError(
        err.response?.data?.error || 'Could not generate a schedule. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await scheduleAPI.createSchedule({
        name: scheduleName,
        semester,
        year,
        course_ids: courses.map((c) => c.id),
        max_credits: maxCredits,
      });
      setSaveOpen(false);
      navigate(`/schedule/${response.data.schedule.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not save the schedule.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card sx={{ mb: 5, border: '1px solid #e2e8f0', borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <AutoAwesomeIcon sx={{ mr: 1.5, fontSize: 24, color: '#475569' }} />
          <Typography variant="h6" fontWeight="600" sx={{ color: '#1e293b' }}>
            Build my {semester} {year} schedule
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Picks from the courses you still need, skipping anything whose
          prerequisites you have not met yet.
        </Typography>

        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap">
          <TextField
            label="Max credits"
            type="number"
            size="small"
            value={maxCredits}
            onChange={(e) => setMaxCredits(parseInt(e.target.value, 10) || 0)}
            inputProps={{ min: 3, max: 24 }}
            sx={{ width: 130 }}
          />
          <Button
            variant="contained"
            onClick={handleGenerate}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <AutoAwesomeIcon />}
          >
            {loading ? 'Generating…' : 'Generate schedule'}
          </Button>
          {courses.length > 0 && (
            <Button variant="outlined" onClick={() => setSaveOpen(true)}>
              Save this schedule
            </Button>
          )}
        </Stack>

        {error && (
          <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {courses.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              {courses.length} course{courses.length === 1 ? '' : 's'} ·{' '}
              {result.schedule.total_credits} credits
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {courses.map((course) => (
                <Chip key={course.id} label={`${course.code} (${course.credits})`} />
              ))}
            </Stack>
          </Box>
        )}

        {result?.conflicts_avoided?.length > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="subtitle2">
              Time conflicts avoided: {result.conflicts_avoided.length}
            </Typography>
            {result.conflicts_avoided.map((c, i) => (
              <Typography key={i} variant="body2" sx={{ ml: 2 }}>
                • {c.course} (conflicts with {c.conflicts_with})
              </Typography>
            ))}
          </Alert>
        )}

        {result?.blocked_by_prerequisites?.length > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Held back until prerequisites are met:{' '}
              {result.blocked_by_prerequisites.length}
            </Typography>
            {result.blocked_by_prerequisites.slice(0, 8).map((item, i) => (
              <Typography key={i} variant="body2" sx={{ ml: 2 }}>
                • <strong>{item.code}</strong> needs{' '}
                {(item.missing_prerequisites || []).join(', ')}
              </Typography>
            ))}
            <Typography variant="body2" sx={{ mt: 1 }}>
              Already taken some of these? Tick them on your degree plan.
            </Typography>
          </Alert>
        )}

        {result?.scheduled_without_times?.length > 0 && (
          <Alert severity="info">
            <Typography variant="subtitle2" gutterBottom>
              Planned, but with no meeting times yet:{' '}
              {result.scheduled_without_times.length}
            </Typography>
            <Typography variant="body2">
              These count toward your credits but could not be checked for time
              conflicts. Add their times once you see them in the registration portal.
            </Typography>
          </Alert>
        )}
      </CardContent>

      <Dialog open={saveOpen} onClose={() => setSaveOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Save schedule</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Schedule name"
            value={scheduleName}
            onChange={(e) => setScheduleName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default GenerateScheduleCard;
