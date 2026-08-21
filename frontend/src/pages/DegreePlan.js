import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Alert,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Checkbox,
  IconButton,
  Paper,
  Stack,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { curriculumAPI } from '../services/api';

const STATUS_COMPLETED = 'completed';
const STATUS_NEEDED = 'needed';

/**
 * A student's degree plan: upload it, confirm what was read from the document,
 * then tick off what has already been taken.
 *
 * The confirmation table and the ongoing plan are deliberately the same table.
 * Extraction is only ever a draft, so the student always sees and corrects it
 * before it becomes their curriculum.
 */
const DegreePlan = () => {
  const [entries, setEntries] = useState([]);
  const [progress, setProgress] = useState(null);
  const [draft, setDraft] = useState(null);
  const [pastedText, setPastedText] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const loadCurriculum = useCallback(async () => {
    try {
      const response = await curriculumAPI.get();
      setEntries(response.data.curriculum || []);
      setProgress(response.data.progress || null);
    } catch (err) {
      setMessage({ type: 'error', text: 'Could not load your degree plan.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurriculum();
  }, [loadCurriculum]);

  const handleExtract = async () => {
    if (!files.length && !pastedText.trim()) {
      setMessage({ type: 'warning', text: 'Add a file or paste your degree plan first.' });
      return;
    }
    setExtracting(true);
    setMessage(null);
    try {
      const response = await curriculumAPI.extract(files, pastedText);
      const courses = response.data.courses || [];
      if (!courses.length) {
        setMessage({
          type: 'warning',
          text: 'No courses were found in that document. Try a clearer screenshot, or add rows by hand.',
        });
      } else {
        setDraft(courses.map((course) => ({ ...course, status: course.status || STATUS_NEEDED })));
        setMessage({
          type: 'info',
          text: `Read ${courses.length} courses. Check them carefully before saving — documents do not always scan cleanly.`,
        });
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Could not read that document.',
      });
    } finally {
      setExtracting(false);
    }
  };

  const handleDraftChange = (index, field, value) => {
    setDraft((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  };

  const handleDraftRemove = (index) => {
    setDraft((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDraftAdd = () => {
    setDraft((prev) => [
      ...(prev || []),
      { course_code: '', title: '', credits: 3, category: 'core', status: STATUS_NEEDED, source: 'manual' },
    ]);
  };

  const handleConfirm = async () => {
    const rows = (draft || []).filter((row) => (row.course_code || '').trim());
    if (!rows.length) {
      setMessage({ type: 'warning', text: 'Nothing to save.' });
      return;
    }
    setSaving(true);
    try {
      await curriculumAPI.save(rows);
      setDraft(null);
      setFiles([]);
      setPastedText('');
      setMessage({ type: 'success', text: `Saved ${rows.length} requirements to your degree plan.` });
      await loadCurriculum();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Could not save your degree plan.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleComplete = async (entry) => {
    const nextStatus = entry.status === STATUS_COMPLETED ? STATUS_NEEDED : STATUS_COMPLETED;
    // Update locally first so ticking a long list stays responsive.
    setEntries((prev) =>
      prev.map((row) => (row.id === entry.id ? { ...row, status: nextStatus } : row))
    );
    try {
      await curriculumAPI.updateEntry(entry.id, { status: nextStatus });
      await loadCurriculum();
    } catch (err) {
      setEntries((prev) =>
        prev.map((row) => (row.id === entry.id ? { ...row, status: entry.status } : row))
      );
      setMessage({ type: 'error', text: 'Could not update that course.' });
    }
  };

  const handleDelete = async (entry) => {
    try {
      await curriculumAPI.deleteEntry(entry.id);
      await loadCurriculum();
    } catch (err) {
      setMessage({ type: 'error', text: 'Could not remove that course.' });
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, mt: 8 }}>
        <CircularProgress />
      </Container>
    );
  }

  const percentComplete =
    progress && progress.credits_total
      ? Math.round((progress.credits_completed / progress.credits_total) * 100)
      : 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4, mt: 8 }}>
      <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
        My Degree Plan
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Your curriculum is the source of truth for what you still need to take.
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 3 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      {progress && progress.total_courses > 0 && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Stack direction="row" spacing={4} flexWrap="wrap" sx={{ mb: 2 }}>
              <Box>
                <Typography variant="h4">{progress.completed_courses}</Typography>
                <Typography variant="body2" color="text.secondary">Completed</Typography>
              </Box>
              <Box>
                <Typography variant="h4">{progress.remaining_courses}</Typography>
                <Typography variant="body2" color="text.secondary">Remaining</Typography>
              </Box>
              <Box>
                <Typography variant="h4">{progress.credits_remaining}</Typography>
                <Typography variant="body2" color="text.secondary">Credits left</Typography>
              </Box>
            </Stack>
            <LinearProgress variant="determinate" value={percentComplete} sx={{ height: 10, borderRadius: 5 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {percentComplete}% of {progress.credits_total} credits
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Upload */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {entries.length ? 'Add to your plan' : 'Upload your curriculum'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload a PDF or screenshots of your degree plan, or paste it as text.
            Scanned PDFs have no readable text — screenshot those instead.
          </Typography>

          <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
            <Button component="label" variant="outlined" startIcon={<UploadIcon />}>
              Choose files
              <input
                hidden
                multiple
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
              />
            </Button>
            {files.map((file) => (
              <Chip key={file.name} label={file.name} size="small" />
            ))}
          </Stack>

          <TextField
            fullWidth
            multiline
            minRows={3}
            label="Or paste your degree plan"
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
            sx={{ mb: 2 }}
          />

          <Button
            variant="contained"
            onClick={handleExtract}
            disabled={extracting}
            startIcon={extracting ? <CircularProgress size={18} /> : null}
          >
            {extracting ? 'Reading document…' : 'Read curriculum'}
          </Button>
        </CardContent>
      </Card>

      {/* Draft confirmation */}
      {draft && (
        <Card sx={{ mb: 4, borderLeft: 4, borderColor: 'warning.main' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Check what we read ({draft.length} courses)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Nothing is saved yet. Fix anything that looks wrong, remove rows that
              are not courses, then save.
            </Typography>

            <TableContainer component={Paper} variant="outlined" sx={{ mb: 2, overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Code</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell align="right">Credits</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Notes</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {draft.map((row, index) => (
                    <TableRow key={index}>
                      <TableCell sx={{ minWidth: 120 }}>
                        <TextField
                          variant="standard"
                          value={row.course_code || ''}
                          onChange={(e) => handleDraftChange(index, 'course_code', e.target.value)}
                        />
                      </TableCell>
                      <TableCell sx={{ minWidth: 180 }}>
                        <TextField
                          variant="standard"
                          fullWidth
                          value={row.title || ''}
                          onChange={(e) => handleDraftChange(index, 'title', e.target.value)}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ width: 90 }}>
                        <TextField
                          variant="standard"
                          type="number"
                          value={row.credits ?? ''}
                          onChange={(e) => handleDraftChange(index, 'credits', e.target.value)}
                        />
                      </TableCell>
                      <TableCell sx={{ minWidth: 110 }}>
                        <TextField
                          variant="standard"
                          value={row.category || ''}
                          onChange={(e) => handleDraftChange(index, 'category', e.target.value)}
                        />
                      </TableCell>
                      <TableCell sx={{ minWidth: 160 }}>
                        <Typography variant="caption" color="text.secondary">
                          {row.already_in_plan ? 'Already in your plan — will be updated. ' : ''}
                          {row.notes || ''}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => handleDraftRemove(index)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleConfirm}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Confirm and save'}
              </Button>
              <Button startIcon={<AddIcon />} onClick={handleDraftAdd}>
                Add a row
              </Button>
              <Button color="inherit" onClick={() => setDraft(null)}>
                Discard
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}

      {/* The plan itself */}
      {entries.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Your requirements
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Tick the courses you have already taken. The rest become the pool your
              schedules are built from.
            </Typography>

            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">Taken</TableCell>
                    <TableCell>Code</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell align="right">Credits</TableCell>
                    <TableCell>When</TableCell>
                    <TableCell>Prerequisites</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {entries.map((entry) => {
                    const done = entry.status === STATUS_COMPLETED || entry.status === 'transferred';
                    return (
                      <TableRow key={entry.id} hover>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={done}
                            onChange={() => handleToggleComplete(entry)}
                          />
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{entry.course_code}</TableCell>
                        <TableCell sx={{ color: done ? 'text.disabled' : 'text.primary' }}>
                          {entry.title || '—'}
                        </TableCell>
                        <TableCell align="right">{entry.credits ?? '—'}</TableCell>
                        <TableCell>
                          {entry.suggested_year ? `Year ${entry.suggested_year}` : ''}
                          {entry.offered_terms?.length ? (
                            <Tooltip title="Terms this course is offered">
                              <Chip
                                size="small"
                                label={entry.offered_terms.join('/')}
                                sx={{ ml: 0.5 }}
                              />
                            </Tooltip>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">
                            {entry.prerequisites?.length ? entry.prerequisites.join(', ') : '—'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <IconButton size="small" onClick={() => handleDelete(entry)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {!entries.length && !draft && (
        <Alert severity="info">
          Once your curriculum is here, schedule generation will only suggest courses
          you actually need, and will hold back anything whose prerequisites you have
          not met yet.
        </Alert>
      )}
    </Container>
  );
};

export default DegreePlan;
