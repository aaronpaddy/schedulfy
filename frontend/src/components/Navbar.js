import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  Divider,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  School as SchoolIcon,
  Schedule as ScheduleIcon,
  Person as PersonIcon,
  Storage as DatasetIcon,
  Logout as LogoutIcon,
  Login as LoginIcon,
  PersonAdd as SignupIcon,
  Settings as SettingsIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, authenticated, logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    handleMenuClose();
    navigate('/login');
  };

  const handleProfile = () => {
    handleMenuClose();
    navigate('/profile');
  };

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
    { label: 'AI Builder', path: '/ai-builder', icon: <AutoAwesomeIcon />, featured: true },
    { label: 'Course Catalog', path: '/courses', icon: <SchoolIcon /> },
    { label: 'Dataset Manager', path: '/dataset-manager', icon: <DatasetIcon /> },
  ];

  const isActive = (path) => {
    return location.pathname === path || 
           (path === '/dashboard' && location.pathname === '/');
  };

  // Don't show navbar on login/signup pages
  const isAuthPage = location.pathname === '/login' || location.pathname === '/signup';
  if (isAuthPage) {
    return null;
  }

  return (
    <AppBar 
      position="fixed" 
      elevation={0}
      sx={{
        background: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(20px)',
      }}
    >
      <Toolbar sx={{ minHeight: '64px' }}>
        <Typography
          variant="h5"
          component="div"
          sx={{ 
            flexGrow: 1, 
            cursor: 'pointer',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            color: 'white',
            letterSpacing: '-0.01em',
            transition: 'all 0.2s ease',
            '&:hover': {
              opacity: 0.9,
            }
          }}
          onClick={() => navigate(authenticated ? '/' : '/login')}
        >
          <SchoolIcon sx={{ fontSize: 28, color: '#3498db' }} />
          Schedulfy
        </Typography>

        {authenticated ? (
          <>
            {/* Navigation items for authenticated users */}
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              {navItems.map((item) => (
                <Button
                  key={item.path}
                  color="inherit"
                  startIcon={item.icon}
                  onClick={() => navigate(item.path)}
                  sx={{
                    backgroundColor: item.featured 
                      ? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
                      : isActive(item.path) 
                        ? 'rgba(52, 152, 219, 0.2)' 
                        : 'rgba(255, 255, 255, 0.05)',
                    background: item.featured 
                      ? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
                      : undefined,
                    color: 'white',
                    borderRadius: 2,
                    px: 2.5,
                    py: 1,
                    fontWeight: item.featured ? 600 : 500,
                    textTransform: 'none',
                    fontSize: '0.875rem',
                    letterSpacing: '0.01em',
                    border: item.featured 
                      ? '1px solid rgba(139, 92, 246, 0.5)'
                      : isActive(item.path) 
                        ? '1px solid rgba(52, 152, 219, 0.3)' 
                        : '1px solid rgba(255, 255, 255, 0.1)',
                    transition: 'all 0.2s ease',
                    boxShadow: item.featured ? '0 4px 12px rgba(139, 92, 246, 0.4)' : undefined,
                    '&:hover': {
                      backgroundColor: isActive(item.path) 
                        ? 'rgba(52, 152, 219, 0.3)' 
                        : 'rgba(255, 255, 255, 0.1)',
                      transform: 'translateY(-1px)',
                      boxShadow: item.featured 
                        ? '0 6px 16px rgba(139, 92, 246, 0.5)'
                        : '0 4px 12px rgba(0, 0, 0, 0.15)',
                    },
                  }}
                >
                  {item.label}
                </Button>
              ))}
            </Box>

            {/* User menu */}
            <Box sx={{ ml: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
              {user && (
                <Typography
                  variant="body2"
                  sx={{
                    color: 'rgba(255, 255, 255, 0.9)',
                    fontWeight: 500,
                  }}
                >
                  {user.username}
                </Typography>
              )}
              <IconButton
                color="inherit"
                onClick={handleMenuOpen}
                sx={{ 
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'scale(1.05)',
                  }
                }}
              >
                <Avatar sx={{ 
                  width: 36, 
                  height: 36, 
                  background: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                  border: '2px solid rgba(255, 255, 255, 0.2)',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                }}>
                  <PersonIcon sx={{ color: 'white', fontSize: 20 }} />
                </Avatar>
              </IconButton>
            </Box>

            {/* User dropdown menu */}
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              PaperProps={{
                sx: {
                  mt: 1.5,
                  minWidth: 200,
                  borderRadius: 2,
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
                }
              }}
            >
              {user && (
                <Box sx={{ px: 2, py: 1.5 }}>
                  <Typography variant="subtitle2" fontWeight="600">
                    {user.username}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {user.email}
                  </Typography>
                </Box>
              )}
              <Divider />
              <MenuItem onClick={handleProfile}>
                <ListItemIcon>
                  <SettingsIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText>Profile Settings</ListItemText>
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout}>
                <ListItemIcon>
                  <LogoutIcon fontSize="small" color="error" />
                </ListItemIcon>
                <ListItemText>
                  <Typography color="error">Logout</Typography>
                </ListItemText>
              </MenuItem>
            </Menu>
          </>
        ) : (
          <>
            {/* Login/Signup buttons for unauthenticated users */}
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Button
                color="inherit"
                startIcon={<LoginIcon />}
                onClick={() => navigate('/login')}
                sx={{
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: 'white',
                  borderRadius: 2,
                  px: 2.5,
                  py: 1,
                  fontWeight: 500,
                  textTransform: 'none',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    transform: 'translateY(-1px)',
                  },
                }}
              >
                Login
              </Button>
              <Button
                variant="contained"
                startIcon={<SignupIcon />}
                onClick={() => navigate('/signup')}
                sx={{
                  background: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                  color: 'white',
                  borderRadius: 2,
                  px: 2.5,
                  py: 1,
                  fontWeight: 500,
                  textTransform: 'none',
                  boxShadow: '0 2px 8px rgba(52, 152, 219, 0.3)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(52, 152, 219, 0.4)',
                  },
                }}
              >
                Sign Up
              </Button>
            </Box>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 