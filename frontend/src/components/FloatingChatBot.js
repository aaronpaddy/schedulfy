import React, { useState } from 'react';
import { Fab, Paper, Box, Typography, IconButton, Slide, useMediaQuery, useTheme } from '@mui/material';
import {
  Chat as ChatIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import AIChatBot from './AIChatBot';

/**
 * The advisor, reachable from anywhere.
 *
 * Chat used to live on its own page, which meant leaving whatever you were
 * doing to ask a question. As a floating panel it stays available while the
 * student reads their plan or a generated schedule.
 */
const FloatingChatBot = () => {
  const [open, setOpen] = useState(false);
  const theme = useTheme();
  const fullWidth = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <>
      {!open && (
        <Fab
          color="primary"
          aria-label="Ask the advisor"
          onClick={() => setOpen(true)}
          sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1300 }}
        >
          <ChatIcon />
        </Fab>
      )}

      <Slide direction="up" in={open} mountOnEnter unmountOnExit>
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            bottom: fullWidth ? 0 : 24,
            right: fullWidth ? 0 : 24,
            left: fullWidth ? 0 : 'auto',
            width: fullWidth ? '100%' : 400,
            maxWidth: '100%',
            height: fullWidth ? '85vh' : 560,
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            borderRadius: fullWidth ? '12px 12px 0 0' : 2,
            zIndex: 1300,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              px: 2,
              py: 1.5,
              borderBottom: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Typography variant="subtitle1" fontWeight="600">
              Schedulfy Advisor
            </Typography>
            <IconButton size="small" onClick={() => setOpen(false)} aria-label="Close chat">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          <Box sx={{ flex: 1, overflow: 'auto', p: 1 }}>
            <AIChatBot />
          </Box>
        </Paper>
      </Slide>
    </>
  );
};

export default FloatingChatBot;
