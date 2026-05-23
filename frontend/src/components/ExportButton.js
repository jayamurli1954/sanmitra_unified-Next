import React from 'react';
import { Button, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import TableChartIcon from '@mui/icons-material/TableChart';
import DescriptionIcon from '@mui/icons-material/Description';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { exportToCSV, exportToExcel, exportToJSON } from '../utils/export';

const ExportButton = ({ 
  data, 
  onExport = null,
  filename = 'export', 
  headers = null,
  variant = 'outlined',
  size = 'medium',
  showMenu = true 
}) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    if (showMenu && (typeof onExport === 'function' || data)) {
      setAnchorEl(event.currentTarget);
    } else if (data) {
      // Direct export to CSV if no menu
      exportToCSV(data, `${filename}.csv`, headers);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExport = (format) => {
    if (typeof onExport === 'function') {
      onExport(format);
      handleClose();
      return;
    }

    if (!data || data.length === 0) {
      return;
    }

    switch (format) {
      case 'csv':
        exportToCSV(data, `${filename}.csv`, headers);
        break;
      case 'excel':
        exportToExcel(data, `${filename}.xlsx`, headers);
        break;
      case 'json':
        exportToJSON(data, `${filename}.json`);
        break;
      default:
        exportToCSV(data, `${filename}.csv`, headers);
    }
    handleClose();
  };

  if (!onExport && (!data || data.length === 0)) {
    return null;
  }

  if (!showMenu) {
    return (
      <Button
        variant={variant}
        size={size}
        startIcon={<FileDownloadIcon />}
        onClick={handleClick}
      >
        Export
      </Button>
    );
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        startIcon={<FileDownloadIcon />}
        onClick={handleClick}
      >
        Export
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem onClick={() => handleExport('csv')}>
          <ListItemIcon>
            <TableChartIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as CSV</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('excel')}>
          <ListItemIcon>
            <TableChartIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as Excel</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('pdf')}>
          <ListItemIcon>
            <PictureAsPdfIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as PDF</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('json')}>
          <ListItemIcon>
            <DescriptionIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as JSON</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};

export default ExportButton;




