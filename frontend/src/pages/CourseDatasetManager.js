import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CloudDownload as DownloadIcon,
  Delete as DeleteIcon,
  Info as InfoIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Language as LanguageIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { courseAPI } from '../services/api';

const CourseDatasetManager = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [deletingCatalog, setDeletingCatalog] = useState(false);
  const [message, setMessage] = useState(null);
  const [importResult, setImportResult] = useState(null);
  
  // Web scraping states
  const [scrapingUrl, setScrapingUrl] = useState('');
  const [scraping, setScraping] = useState(false);
  const [enhancedScraping, setEnhancedScraping] = useState(false);
  const [scrapedCourses, setScrapedCourses] = useState([]);
  const [selectedScrapedCourses, setSelectedScrapedCourses] = useState([]);
  const [scrapeDialogOpen, setScrapeDialogOpen] = useState(false);
  const [scrapeResult, setScrapeResult] = useState(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.type === 'text/csv' || file.name.endsWith('.csv') || 
          file.type === 'application/json' || file.name.endsWith('.json')) {
        setSelectedFile(file);
        setMessage(null);
      } else {
        setMessage({
          type: 'error',
          text: 'Please select a CSV or JSON file'
        });
        setSelectedFile(null);
      }
    }
  };

  const handleImport = async () => {
    if (!selectedFile) return;

    setImporting(true);
    setMessage(null);
    setImportResult(null);

    try {
      const response = await courseAPI.importCourses(selectedFile);
      setImportResult(response.data);
      setMessage({
        type: 'success',
        text: `Import completed successfully! Imported: ${response.data.imported}, Updated: ${response.data.updated}`
      });
      setSelectedFile(null);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Import failed'
      });
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await courseAPI.exportCourses();
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'courses_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setMessage({
        type: 'success',
        text: 'Courses exported successfully!'
      });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Export failed'
      });
    } finally {
      setExporting(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm('Are you sure you want to clear all courses? This action cannot be undone.')) {
      return;
    }

    setClearing(true);
    try {
      await courseAPI.clearCourses();
      setMessage({
        type: 'success',
        text: 'All courses cleared successfully!'
      });
      setImportResult(null);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to clear courses'
      });
    } finally {
      setClearing(false);
    }
  };

  const handleDeleteCatalog = async () => {
    if (!window.confirm('Are you sure you want to delete the course catalog? This will remove all imported courses but keep your schedules and user data. This action cannot be undone.')) {
      return;
    }

    setDeletingCatalog(true);
    try {
      await courseAPI.clearCourses();
      setMessage({
        type: 'success',
        text: 'Course catalog deleted successfully! Your schedules and user data remain intact.'
      });
      setImportResult(null);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to delete course catalog'
      });
    } finally {
      setDeletingCatalog(false);
    }
  };

  const handleScrapeUrl = async () => {
    if (!scrapingUrl.trim()) return;

    setScraping(true);
    setMessage(null);
    setScrapeResult(null);

    try {
      const response = await courseAPI.scrapeCourses(scrapingUrl.trim(), enhancedScraping);
      const courses = response.data.courses || [];
      setScrapedCourses(courses);
      setScrapeResult(response.data);
      
      // Auto-select all courses by default for easier import
      setSelectedScrapedCourses(courses.map(course => course.code));
      setScrapeDialogOpen(true);
      
      setMessage({
        type: 'success',
        text: `Successfully scraped ${response.data.total_found} courses from ${scrapingUrl}${enhancedScraping ? ' with enhanced schedule info' : ''}`
      });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Web scraping failed'
      });
    } finally {
      setScraping(false);
    }
  };

  const handleImportScrapedCourses = async () => {
    if (selectedScrapedCourses.length === 0) return;

    setImporting(true);
    setMessage(null);

    try {
      // We need to get the full course objects, not just the codes
      // The scrapedCourses array contains the actual course objects
      const coursesToImport = scrapedCourses.filter(course => 
        selectedScrapedCourses.includes(course.code)
      );
      
      console.log('Courses to import:', coursesToImport); // Debug log
      console.log('Number of courses to import:', coursesToImport.length); // Debug log

      // Create a mock file object for the import function
      // The backend expects just the array of courses, not the full response object
      const mockFile = new File(
        [JSON.stringify(coursesToImport)],
        'scraped_courses.json',
        { type: 'application/json' }
      );

      const response = await courseAPI.importCourses(mockFile);
      setImportResult(response.data);
      
      // Show success message with option to build schedule with AI
      setMessage({
        type: 'success',
        text: `Successfully imported ${response.data.imported} scraped courses! You can now generate a schedule with these courses.`
      });
      
      // Close dialog and reset
      setScrapeDialogOpen(false);
      setScrapedCourses([]);
      setSelectedScrapedCourses([]);
      setScrapingUrl('');
      
              // Show option to navigate to schedule generator
        if (response.data.imported > 0) {
          if (window.confirm(`Great! ${response.data.imported} courses have been imported. Would you like to go to the AI Schedule Builder to create a schedule with these courses?`)) {
            // Navigate to AI schedule builder using React Router
            navigate('/ai-builder');
          }
        }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to import scraped courses'
      });
    } finally {
      setImporting(false);
    }
  };

  const handleSelectAllScrapedCourses = () => {
    if (selectedScrapedCourses.length === scrapedCourses.length) {
      setSelectedScrapedCourses([]);
    } else {
      setSelectedScrapedCourses(scrapedCourses.map(course => course.code));
    }
  };

  const handleToggleScrapedCourse = (courseCode) => {
    setSelectedScrapedCourses(prev => 
      prev.includes(courseCode)
        ? prev.filter(code => code !== courseCode)
        : [...prev, courseCode]
    );
  };

  const getFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4, mt: 8 }}>
      <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 600, mb: 4 }}>
        Course Dataset Manager
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 3 }}>
          {message.text}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Import Section */}
        <Grid item xs={12} md={6}>
          <Paper elevation={0} sx={{ p: 3, height: 'fit-content' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <UploadIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
              <Typography variant="h4" fontWeight="600" color="primary.main">
                Import Courses
              </Typography>
            </Box>

            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Upload a CSV or JSON file to import course data. The file should contain course information
              including course codes, names, credits, and other details.
            </Typography>

            <Box sx={{ mb: 3 }}>
              <input
                accept=".csv,.json"
                style={{ display: 'none' }}
                id="file-upload"
                type="file"
                onChange={handleFileSelect}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadIcon />}
                  sx={{ mb: 2 }}
                  fullWidth
                >
                  Select File
                </Button>
              </label>

              {selectedFile && (
                <Card variant="outlined" sx={{ mt: 2 }}>
                  <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="subtitle2" fontWeight="600">
                          {selectedFile.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {getFileSize(selectedFile.size)} • {selectedFile.type || 'Unknown type'}
                        </Typography>
                      </Box>
                      <CheckIcon color="success" />
                    </Box>
                  </CardContent>
                </Card>
              )}
            </Box>

            <Button
              variant="contained"
              onClick={handleImport}
              disabled={!selectedFile || importing}
              startIcon={importing ? <CircularProgress size={20} /> : <UploadIcon />}
              fullWidth
              sx={{
                background: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: '0 6px 16px rgba(52, 152, 219, 0.4)',
                },
                transition: 'all 0.2s ease',
              }}
            >
              {importing ? 'Importing...' : 'Import Courses'}
            </Button>
          </Paper>
        </Grid>

        {/* Web Scraping Section */}
        <Grid item xs={12} md={6}>
          <Paper elevation={0} sx={{ p: 3, height: 'fit-content' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <LanguageIcon sx={{ mr: 2, fontSize: 32, color: 'success.main' }} />
              <Typography variant="h4" fontWeight="600" color="success.main">
                Web Scraping
              </Typography>
            </Box>

            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Enter a university course catalog URL to automatically scrape and import course information.
              This feature works with most university websites that display course listings.
            </Typography>

            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                label="Course Catalog URL"
                placeholder="https://example.edu/courses or https://example.edu/department/courses"
                value={scrapingUrl}
                onChange={(e) => setScrapingUrl(e.target.value)}
                sx={{ mb: 2 }}
                helperText="Enter the URL of a page that lists courses (e.g., course catalog, department page)"
              />
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Checkbox
                  checked={enhancedScraping}
                  onChange={(e) => setEnhancedScraping(e.target.checked)}
                  color="primary"
                />
                <Typography variant="body2" color="text.secondary">
                  Enhanced scraping (get time slots, days, and rooms - slower but more complete)
                </Typography>
              </Box>
              
              <Button
                variant="contained"
                onClick={handleScrapeUrl}
                disabled={!scrapingUrl.trim() || scraping}
                startIcon={scraping ? <CircularProgress size={20} /> : <LanguageIcon />}
                fullWidth
                sx={{
                  background: 'linear-gradient(135deg, #4caf50 0%, #388e3c 100%)',
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: '0 6px 16px rgba(76, 175, 80, 0.4)',
                  },
                  transition: 'all 0.2s ease',
                }}
              >
                {scraping ? 'Scraping...' : 'Scrape Courses from URL'}
              </Button>
            </Box>

            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Supported formats:</strong> Most university course catalog websites
                <br />
                <strong>What gets scraped:</strong> Course codes, names, credits, departments, descriptions
                <br />
                <strong>Note:</strong> Some websites may require manual review of scraped data
              </Typography>
            </Alert>
          </Paper>
        </Grid>

        {/* Export & Clear Section */}
        <Grid item xs={12} md={6}>
          <Paper elevation={0} sx={{ p: 3, height: 'fit-content' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <DownloadIcon sx={{ mr: 2, fontSize: 32, color: 'secondary.main' }} />
              <Typography variant="h4" fontWeight="600" color="secondary.main">
                Export & Manage
              </Typography>
            </Box>

            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Export your current course database or clear all courses to start fresh.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={handleExport}
                disabled={exporting}
                startIcon={exporting ? <CircularProgress size={20} /> : <DownloadIcon />}
                fullWidth
                sx={{
                  borderColor: 'secondary.main',
                  color: 'secondary.main',
                  '&:hover': {
                    borderColor: 'secondary.dark',
                    backgroundColor: 'rgba(52, 152, 219, 0.04)',
                  },
                }}
              >
                {exporting ? 'Exporting...' : 'Export Courses (CSV)'}
              </Button>

              <Button
                variant="outlined"
                onClick={handleClear}
                disabled={clearing}
                startIcon={clearing ? <CircularProgress size={20} /> : <DeleteIcon />}
                fullWidth
                color="error"
                sx={{
                  '&:hover': {
                    backgroundColor: 'rgba(244, 67, 54, 0.04)',
                  },
                }}
              >
                {clearing ? 'Clearing...' : 'Clear All Courses'}
              </Button>

              <Button
                variant="outlined"
                onClick={handleDeleteCatalog}
                disabled={deletingCatalog}
                startIcon={deletingCatalog ? <CircularProgress size={20} /> : <DeleteIcon />}
                fullWidth
                color="warning"
                sx={{
                  borderColor: 'warning.main',
                  color: 'warning.main',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 152, 0, 0.04)',
                  },
                }}
              >
                {deletingCatalog ? 'Deleting...' : 'Delete Course Catalog'}
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Import Results */}
        {importResult && (
          <Grid item xs={12}>
            <Paper elevation={0} sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                Import Results
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <Card sx={{ 
                    background: 'linear-gradient(135deg, #4caf50 0%, #388e3c 100%)',
                    color: 'white'
                  }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h3" fontWeight="600">
                        {importResult.imported}
                      </Typography>
                      <Typography variant="subtitle1">
                        New Courses
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card sx={{ 
                    background: 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)',
                    color: 'white'
                  }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h3" fontWeight="600">
                        {importResult.updated}
                      </Typography>
                      <Typography variant="subtitle1">
                        Updated Courses
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card sx={{ 
                    background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
                    color: 'white'
                  }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h3" fontWeight="600">
                        {importResult.errors?.length || 0}
                      </Typography>
                      <Typography variant="subtitle1">
                        Errors
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {importResult.errors && importResult.errors.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Import Errors
                  </Typography>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Some courses had issues during import. Check the details below.
                  </Alert>
                  {importResult.errors.map((error, index) => (
                    <Chip
                      key={index}
                      label={error}
                      color="warning"
                      variant="outlined"
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>
              )}
            </Paper>
          </Grid>
        )}

        {/* File Format Guide */}
        <Grid item xs={12}>
          <Paper elevation={0} sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <InfoIcon sx={{ mr: 2, fontSize: 28, color: 'info.main' }} />
              <Typography variant="h5" fontWeight="600" color="info.main">
                File Format Guide
              </Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  CSV Format
                </Typography>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Your CSV file should have the following columns:
                </Typography>
                <Box component="code" sx={{ 
                  display: 'block', 
                  p: 2, 
                  bgcolor: 'grey.50', 
                  borderRadius: 1,
                  fontSize: '0.875rem',
                  fontFamily: 'monospace'
                }}>
                  course_code,course_name,description,credits,department,prerequisites,semester,year,time_slots,max_capacity,current_enrollment
                </Box>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  JSON Format
                </Typography>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Your JSON file should be an array of course objects:
                </Typography>
                <Box component="code" sx={{ 
                  display: 'block', 
                  p: 2, 
                  bgcolor: 'grey.50', 
                  borderRadius: 1,
                  fontSize: '0.875rem',
                  fontFamily: 'monospace'
                }}>
                  {`[{"course_code": "CS101", "course_name": "Intro to CS", "credits": 3}]`}
                </Box>
              </Grid>
            </Grid>

            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Required fields:</strong> course_code, course_name, credits
                <br />
                <strong>Optional fields:</strong> description, department, prerequisites, semester, year, time_slots, max_capacity, current_enrollment
              </Typography>
            </Alert>
          </Paper>
        </Grid>
      </Grid>

      {/* Scraped Courses Review Dialog */}
      <Dialog
        open={scrapeDialogOpen}
        onClose={() => setScrapeDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h5" fontWeight="600">
              Review Scraped Courses
            </Typography>
            <Button
              onClick={handleSelectAllScrapedCourses}
              variant="outlined"
              size="small"
              startIcon={<AddIcon />}
            >
              {selectedScrapedCourses.length === scrapedCourses.length ? 'Deselect All' : 'Select All'}
            </Button>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Found {scrapedCourses.length} courses from {scrapeResult?.url}. 
            Select the courses you want to import into your database.
          </Typography>
          
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>💡 Tip:</strong> All courses are pre-selected by default. 
              After importing, you'll be able to build schedules with these courses using the AI Builder!
            </Typography>
          </Alert>

          {scrapeResult && (
            <Alert severity="success" sx={{ mb: 3 }}>
              <Typography variant="body2">
                <strong>Scraping Results:</strong> {scrapeResult.message}
                <br />
                <strong>URL:</strong> {scrapeResult.url}
              </Typography>
            </Alert>
          )}

          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {scrapedCourses.map((course) => (
              <ListItem key={course.code} divider>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" component="span" fontWeight="bold">
                        {course.code}
                      </Typography>
                      <Chip 
                        label={`${course.credits} credits`} 
                        size="small" 
                        color="primary" 
                        variant="outlined"
                      />
                      <Chip 
                        label={course.department} 
                        size="small" 
                        color="secondary" 
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
                        {course.name}
                      </Typography>
                      {course.description && (
                        <Typography variant="body2" component="span" color="text.secondary" sx={{ mt: 0.5 }}>
                          {course.description}
                        </Typography>
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <Checkbox
                    edge="end"
                    checked={selectedScrapedCourses.includes(course.code)}
                    onChange={() => handleToggleScrapedCourse(course.code)}
                  />
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setScrapeDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleImportScrapedCourses}
            variant="contained"
            disabled={selectedScrapedCourses.length === 0 || importing}
            startIcon={importing ? <CircularProgress size={20} /> : <AddIcon />}
            sx={{
              background: 'linear-gradient(135deg, #4caf50 0%, #388e3c 100%)',
              '&:hover': {
                transform: 'translateY(-1px)',
                boxShadow: '0 6px 16px rgba(76, 175, 80, 0.4)',
              },
            }}
          >
            {importing ? 'Importing...' : `Import ${selectedScrapedCourses.length} Selected Courses`}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default CourseDatasetManager; 