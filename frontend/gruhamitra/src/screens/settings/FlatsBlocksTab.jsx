import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import flatsService from '../../services/flatsService';
import memberOnboardingService from '../../services/memberOnboardingService';
import { getErrorMessage } from './settingsHelpers';

const FlatsBlocksTab = () => {
  const [flats, setFlats] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [debugMessages, setDebugMessages] = useState([]);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [blocksConfig, setBlocksConfig] = useState([]);
  const [editingBlock, setEditingBlock] = useState(null);

  const addDebugMessage = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugMessages(prev => [...prev.slice(-19), { timestamp, message, type }]);
  };

  const sanitizeBlocksConfig = (blocks) => {
    if (!Array.isArray(blocks)) return [];
    return blocks
      .filter((entry) => entry && typeof entry === 'object')
      .map((entry, index) => {
        const name = String(entry.name || String.fromCharCode(65 + (index % 26)))
          .trim()
          .toUpperCase()
          .slice(0, 10) || 'A';
        const floors = Math.max(1, Math.min(200, parseInt(entry.floors, 10) || 1));
        const flatsPerFloor = Math.max(1, Math.min(200, parseInt(entry.flatsPerFloor, 10) || 1));
        const fromArray = Array.isArray(entry.flatsByFloor)
          ? entry.flatsByFloor
          : [];
        const fromText = !fromArray.length && typeof entry.flatsByFloorText === 'string'
          ? parseFlatsByFloorInput(entry.flatsByFloorText)
          : [];
        const flatsByFloor = (fromArray.length ? fromArray : fromText)
          .map((n) => Math.max(1, Math.min(200, parseInt(n, 10) || 0)))
          .filter((n) => n > 0)
          .slice(0, floors);
        return {
          name,
          floors,
          flatsPerFloor,
          flatsByFloor,
          customPerFloor: flatsByFloor.length > 0,
        };
      });
  };

  const parseFlatsByFloorInput = (value) => {
    if (!value || !String(value).trim()) return [];
    return String(value)
      .split(',')
      .map((n) => parseInt(n.trim(), 10))
      .filter((n) => Number.isInteger(n) && n > 0)
      .slice(0, 200);
  };

  const blockTotalFlats = (block) => {
    const custom = Array.isArray(block?.flatsByFloor) && block.flatsByFloor.length > 0
      ? block.flatsByFloor
      : parseFlatsByFloorInput(block?.flatsByFloorText || '');
    if (custom.length > 0) {
      return custom.reduce((sum, n) => sum + (parseInt(n, 10) || 0), 0);
    }
    return (parseInt(block?.floors, 10) || 0) * (parseInt(block?.flatsPerFloor, 10) || 0);
  };

  const ensureCustomFloorCounts = (block) => {
    const floors = Math.max(1, parseInt(block?.floors, 10) || 1);
    const fallback = Math.max(1, parseInt(block?.flatsPerFloor, 10) || 1);
    const current = Array.isArray(block?.flatsByFloor) ? block.flatsByFloor : [];
    const next = [];
    for (let i = 0; i < floors; i += 1) {
      const parsed = parseInt(current[i], 10);
      next.push(Number.isInteger(parsed) && parsed > 0 ? Math.min(parsed, 200) : fallback);
    }
    return next;
  };

  // Flat form state
  const [flatForm, setFlatForm] = useState({
    flat_number: '',
    area_sqft: '',
    flat_type: '',
    status: 'Vacant',
    parking_slots: '',
  });

  useEffect(() => {
    loadData();
    loadBlocksConfig();
  }, []);

  // Debug effect to log when members/flats are loaded
  useEffect(() => {
    if (members.length > 0 && flats.length > 0) {
      const a304Member = members.find(m => {
        const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
        return mFlat === 'A-304';
      });
      const a304Flat = flats.find(f => {
        const fFlat = (f.flat_number || f.flatNumber || '').trim().toUpperCase();
        return fFlat === 'A-304';
      });

      console.log(' A-304 Data Check:', {
        member: a304Member,
        flat: a304Flat,
        allMembersCount: members.length,
        allFlatsCount: flats.length,
        memberFlatNumbers: members.map(m => (m.flat_number || m.flatNumber || '').trim().toUpperCase()).slice(0, 5),
        flatNumbers: flats.map(f => (f.flat_number || f.flatNumber || '').trim().toUpperCase()).slice(0, 5)
      });
    }
  }, [members, flats]);

  const loadBlocksConfig = async () => {
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings && settings.blocks_config) {
        const normalized = sanitizeBlocksConfig(settings.blocks_config);
        setBlocksConfig(normalized);
        addDebugMessage(` Loaded blocks config: ${JSON.stringify(normalized)}`, 'success');
      } else {
        setBlocksConfig([]);
        addDebugMessage(' No blocks config found', 'warning');
      }
    } catch (error) {
      console.error('Error loading blocks config:', error);
      addDebugMessage(` Error loading blocks config: ${error.message}`, 'error');
      setBlocksConfig([]);
    }
  };

  const handleSaveBlocksConfig = async (nextBlocksConfig = blocksConfig) => {
    const uiBlocks = sanitizeBlocksConfig(nextBlocksConfig);
    setBlocksConfig(uiBlocks);
    const payloadBlocks = uiBlocks.map((block) => ({
      name: block.name,
      floors: block.floors,
      flatsPerFloor: block.flatsPerFloor,
      flatsByFloor: block.customPerFloor ? (block.flatsByFloor || []).slice(0, block.floors) : [],
    }));
    setSaving(true);
    try {
      await settingsService.saveSocietySettings({
        blocks_config: payloadBlocks
      });
      addDebugMessage('Blocks configuration saved successfully!', 'success');
      alert('Blocks configuration saved successfully!');
    } catch (error) {
      console.error('Error saving blocks config:', error);
      const saveError = getErrorMessage(error);
      addDebugMessage(`Error saving blocks config: ${saveError}`, 'error');
      alert(`Failed to save blocks configuration: ${saveError}`);
      setSaving(false);
      return;
    }

    try {
      // Reload flats after save; reload issues should not report as save failure.
      await loadData();
    } catch (reloadError) {
      const reloadMessage = getErrorMessage(reloadError);
      addDebugMessage(`Saved, but refresh failed: ${reloadMessage}`, 'warning');
      alert(`Blocks saved, but refresh failed: ${reloadMessage}`);
    } finally {
      setSaving(false);
    }
  };

  const handleEditBlock = (index) => {
    setEditingBlock(index);
  };

  const handleUpdateBlock = (index, field, value) => {
    const updated = [...blocksConfig];
    const next = { ...updated[index], [field]: value };
    if (field === 'floors') {
      const floors = Math.max(1, parseInt(value, 10) || 1);
      if (next.customPerFloor) {
        next.flatsByFloor = ensureCustomFloorCounts({ ...next, floors });
      }
    }
    if (field === 'customPerFloor') {
      if (value) {
        next.flatsByFloor = ensureCustomFloorCounts(next);
      } else {
        next.flatsByFloor = [];
      }
    }
    updated[index] = next;
    setBlocksConfig(updated);
  };

  const handleCustomFloorCountChange = (blockIndex, floorIndex, value) => {
    const updated = [...blocksConfig];
    const block = { ...updated[blockIndex] };
    const counts = ensureCustomFloorCounts(block);
    counts[floorIndex] = Math.max(1, Math.min(200, parseInt(value, 10) || 1));
    block.flatsByFloor = counts;
    block.customPerFloor = true;
    updated[blockIndex] = block;
    setBlocksConfig(updated);
  };

  const handleSaveBlock = (index) => {
    setEditingBlock(null);
    // Auto-save when editing is done
    handleSaveBlocksConfig();
  };

  const handleAddBlock = () => {
    const newBlock = {
      name: String.fromCharCode(65 + blocksConfig.length),
      floors: 4,
      flatsPerFloor: 5,
      flatsByFloor: [],
      customPerFloor: false,
    };
    setBlocksConfig([...blocksConfig, newBlock]);
    setEditingBlock(blocksConfig.length);
  };

  const handleDeleteBlock = async (index) => {
    if (!confirm('Are you sure you want to delete this block? This will also delete all flats in this block.')) {
      return;
    }
    const updated = blocksConfig.filter((_, i) => i !== index);
    setBlocksConfig(updated);
    await handleSaveBlocksConfig(updated);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // Load flats and members separately to handle errors better
      let flatsList = [];
      let membersList = [];

      try {
        flatsList = await flatsService.getFlats();
        const count = flatsList?.length || 0;
        console.log(' Flats loaded:', count, 'flats');
        addDebugMessage(` Loaded ${count} flats successfully`, 'success');
        // Ensure flatsList is an array
        if (!Array.isArray(flatsList)) {
          console.warn(' Flats response is not an array:', flatsList);
          addDebugMessage(` Flats response is not an array: ${JSON.stringify(flatsList)}`, 'warning');
          flatsList = [];
        }
        // Debug: Check if flats have ID field
        if (flatsList.length > 0) {
          const sampleFlat = flatsList[0];
          console.log(' Sample flat structure:', {
            hasId: 'id' in sampleFlat,
            has_id: '_id' in sampleFlat,
            idValue: sampleFlat.id || sampleFlat._id,
            allKeys: Object.keys(sampleFlat),
            flatNumber: sampleFlat.flat_number
          });
          addDebugMessage(` Sample flat keys: ${Object.keys(sampleFlat).join(', ')}`, 'info');
          if (!sampleFlat.id && !sampleFlat._id) {
            console.error(' WARNING: Flats are missing ID field!');
            addDebugMessage(' WARNING: Flats are missing ID field!', 'error');
          }
        }
      } catch (flatsError) {
        console.error(' Error loading flats:', flatsError);
        const flatsErrorMsg = flatsError.response?.data?.detail || flatsError.message || 'Failed to load flats';
        const errorDetails = {
          status: flatsError.response?.status,
          data: flatsError.response?.data,
          message: flatsErrorMsg,
          url: flatsError.config?.url
        };
        console.error('Flats error details:', errorDetails);
        addDebugMessage(` Error loading flats: ${flatsErrorMsg}`, 'error');
        addDebugMessage(`Details: Status ${errorDetails.status}, URL: ${errorDetails.url}`, 'error');
        // Continue even if flats fail - show error but don't block
        console.warn(`Warning: Could not load flats. ${flatsErrorMsg}`);
        flatsList = []; // Set to empty array on error
      }

      try {
        membersList = await memberOnboardingService.listMembers();
        console.log(' Members loaded:', membersList?.length || 0, 'members');
        // Ensure membersList is an array
        if (!Array.isArray(membersList)) {
          console.warn(' Members response is not an array:', membersList);
          membersList = [];
        }
      } catch (membersError) {
        console.error(' Error loading members:', membersError);
        const membersErrorMsg = membersError.response?.data?.detail || membersError.message || 'Failed to load members';
        console.error('Members error details:', {
          status: membersError.response?.status,
          data: membersError.response?.data,
          message: membersErrorMsg
        });
        // Continue even if members fail - show error but don't block
        console.warn(`Warning: Could not load members. ${membersErrorMsg}`);
        membersList = []; // Set to empty array on error
      }

      setFlats(flatsList || []);
      setMembers(membersList || []);

      // Debug: Log A-304 data after loading
      if (membersList && membersList.length > 0) {
        const a304Member = membersList.find(m => {
          const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
          return mFlat === 'A-304';
        });
        console.log(' After Loading - A-304 Member:', a304Member);
        if (a304Member) {
          addDebugMessage(` Found A-304 member: ${a304Member.name} (${a304Member.status})`, 'success');
        } else {
          addDebugMessage(` A-304 member not found in ${membersList.length} members`, 'warning');
          console.log('All member flat numbers:', membersList.map(m => (m.flat_number || m.flatNumber || 'N/A')));
        }
      }
    } catch (error) {
      console.error(' Unexpected error loading data:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to load data. Please check your connection and try again.';
      console.error('Unexpected error:', errorMsg);
      setFlats([]);
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  // Convert bedrooms to BHK format
  const bedroomsToBHK = (bedrooms) => {
    if (!bedrooms) return '';
    if (bedrooms === 1) return '1 BHK';
    if (bedrooms === 2) return '2 BHK';
    if (bedrooms === 3) return '3 BHK';
    if (bedrooms === 4) return '4 BHK';
    return `${bedrooms} BHK`;
  };

  // Convert BHK to bedrooms number
  const bhkToBedrooms = (bhk) => {
    if (!bhk) return null;
    const match = bhk.match(/^(\d+)\s*BHK/i);
    return match ? parseInt(match[1]) : null;
  };

  // Auto-generate parking slot from flat number
  // Examples: A-101  "101", A-102  "102", A-201  "201", A-302  "302"
  const generateParkingSlot = (flatNumber) => {
    if (!flatNumber) return '';
    // Extract numeric part after dash/hyphen
    // Matches patterns like: A-101, 1-201, A-302, etc.
    const match = flatNumber.match(/[-_](\d+)$/);
    if (match) {
      return match[1]; // Return the numeric part
    }
    // If no dash found, try to extract any trailing numbers
    const numMatch = flatNumber.match(/(\d+)$/);
    return numMatch ? numMatch[1] : '';
  };

  // Auto-fill flat details when flat number changes
  const handleFlatNumberChange = (flatNumber) => {
    setFlatForm(prev => ({ ...prev, flat_number: flatNumber }));

    if (!flatNumber.trim()) {
      // Clear form if flat number is empty
      setFlatForm({
        flat_number: '',
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: '',
      });
      return;
    }

    // Normalize flat number for comparison
    const normalizedFlatNumber = flatNumber.trim().toUpperCase();

    // Find existing flat - handle both flat_number and flatNumber field names
    const existingFlat = flats.find(f => {
      const fFlatNumber = (f.flat_number || f.flatNumber || '').trim().toUpperCase();
      return fFlatNumber === normalizedFlatNumber;
    });

    // Find existing member for this flat - use same logic as table display
    const existingMember = members.find(m => {
      const memberFlatNumber = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
      const isActive = m.status === 'active';
      const hasNoMoveOut = !m.move_out_date || new Date(m.move_out_date) > new Date();

      return memberFlatNumber === normalizedFlatNumber && isActive && hasNoMoveOut;
    });

    if (existingFlat || existingMember) {
      // Get flat data - prefer existing flat, otherwise find flat by member's flat_id
      let flatData = existingFlat;
      if (!flatData && existingMember) {
        flatData = flats.find(f => f.id === existingMember.flat_id || f.flat_number === existingMember.flat_number);
      }

      // Auto-fill form from existing data
      const trimmedFlatNumber = flatNumber.trim();
      const autoParkingSlot = generateParkingSlot(trimmedFlatNumber);

      // Ensure area_sqft is properly loaded - use flatData.area_sqft if it exists (even if 0)
      const loadedArea = flatData && flatData.area_sqft !== undefined && flatData.area_sqft !== null
        ? String(flatData.area_sqft)
        : '';

      console.log(' Loading flat data:', {
        flatNumber: trimmedFlatNumber,
        flatData: flatData,
        area_sqft: flatData?.area_sqft,
        loadedArea: loadedArea
      });
      addDebugMessage(` Loading flat: ${trimmedFlatNumber}, Area: ${loadedArea || 'N/A'}`, 'info');

      setFlatForm(prev => ({
        ...prev,
        flat_number: trimmedFlatNumber,
        area_sqft: loadedArea, // Always use loaded area, even if empty
        flat_type: flatData?.bedrooms ? bedroomsToBHK(flatData.bedrooms) : '',
        status: existingMember
          ? (existingMember.member_type === 'owner' ? 'Owner Occupied' : 'Tenant')
          : (flatData?.occupancy_status === 'OWNER_OCCUPIED' ? 'Owner Occupied' :
            flatData?.occupancy_status === 'TENANT_OCCUPIED' ? 'Tenant' : 'Vacant'),
        parking_slots: (flatData?.parking_slots ? String(flatData.parking_slots) : autoParkingSlot),
      }));
    } else {
      // Flat doesn't exist yet, keep flat number but clear other fields
      const trimmedFlatNumber = flatNumber.trim();
      const autoParkingSlot = generateParkingSlot(trimmedFlatNumber);

      setFlatForm(prev => ({
        ...prev,
        flat_number: trimmedFlatNumber,
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: autoParkingSlot, // Auto-generate parking slot from flat number
      }));
    }
  };

  const handleAddFlat = async (e) => {
    // Prevent form submission if called from a form
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    console.log(' handleAddFlat called', {
      flatForm,
      saving,
      loading,
      flatNumber: flatForm.flat_number,
      areaSqft: flatForm.area_sqft
    });
    addDebugMessage(' Button clicked - handleAddFlat called', 'info');
    addDebugMessage(`Form data: Flat=${flatForm.flat_number}, Area=${flatForm.area_sqft}`, 'info');

    if (!flatForm.flat_number.trim()) {
      addDebugMessage(' Validation: Please enter flat number', 'error');
      alert('Please enter flat number');
      return;
    }
    if (!flatForm.area_sqft || parseFloat(flatForm.area_sqft) <= 0) {
      addDebugMessage(' Validation: Please enter valid flat size', 'error');
      alert('Please enter valid flat size');
      return;
    }

    setSaving(true);
    addDebugMessage(` Starting save operation for flat: ${flatForm.flat_number.trim()}`, 'info');
    try {
      const bedrooms = bhkToBedrooms(flatForm.flat_type);

      // Check if flat already exists
      // Handle both 'id' and '_id' field names (backend model uses alias)
      const existingFlat = flats.find(f => {
        const flatNum = f.flat_number || f.flatNumber;
        return flatNum === flatForm.flat_number.trim();
      });

      console.log(' Searching for flat:', {
        searchNumber: flatForm.flat_number.trim(),
        totalFlats: flats.length,
        flatNumbers: flats.map(f => ({
          number: f.flat_number || f.flatNumber,
          id: f.id || f._id,
          hasId: !!(f.id || f._id)
        })),
        found: existingFlat ? 'YES' : 'NO',
        foundFlat: existingFlat
      });
      addDebugMessage(` Searching for flat: ${flatForm.flat_number.trim()}, Found: ${existingFlat ? 'YES' : 'NO'}`, 'info');

      if (existingFlat) {
        // Get ID - handle both 'id' and '_id' field names
        const flatId = existingFlat.id || existingFlat._id;

        // Update existing flat
        console.log(' Existing flat data:', {
          id: flatId,
          idType: typeof flatId,
          hasId: !!existingFlat.id,
          has_id: !!existingFlat._id,
          flat_number: existingFlat.flat_number || existingFlat.flatNumber,
          area_sqft: existingFlat.area_sqft || existingFlat.areaSqft,
          allKeys: Object.keys(existingFlat)
        });
        addDebugMessage(` Found flat - ID: ${flatId}, Type: ${typeof flatId}`, 'info');

        if (!flatId && flatId !== 0 && flatId !== '0') {
          addDebugMessage(` Error: Flat found but ID is missing. Flat data: ${JSON.stringify(existingFlat)}`, 'error');
          addDebugMessage(`Available keys: ${Object.keys(existingFlat).join(', ')}`, 'error');
          alert('Error: Flat ID is missing. Please refresh the page and try again.');
          return;
        }

        const updateData = {
          area_sqft: parseFloat(flatForm.area_sqft),
          parking_slots: (flatForm.parking_slots || '').trim() || null,
        };

        if (bedrooms) {
          updateData.bedrooms = bedrooms;
        }

        // Use the ID we extracted (handles both 'id' and '_id')
        const flatIdToUpdate = flatId;

        console.log(' Updating flat:', {
          flatId: flatIdToUpdate,
          flatNumber: existingFlat.flat_number || existingFlat.flatNumber,
          updateData: updateData
        });
        addDebugMessage(` Updating flat ID: ${flatIdToUpdate}, Number: ${existingFlat.flat_number || existingFlat.flatNumber}`, 'info');

        // Note: occupancy_status update might need to be done separately via member onboarding
        // For now, we'll update what we can through the flat update endpoint
        await flatsService.updateFlat(flatIdToUpdate, updateData);
        addDebugMessage(` Flat "${existingFlat.flat_number}" updated successfully!`, 'success');
        alert('Flat updated successfully!');
      } else {
        // Create new flat - backend requires owner_name, so use a placeholder
        const flatData = {
          flat_number: flatForm.flat_number.trim(),
          area_sqft: parseFloat(flatForm.area_sqft),
          bedrooms: bedrooms || 2, // Default to 2 if not specified
          parking_slots: (flatForm.parking_slots || '').trim() || null,
          occupants: 1,
          owner_name: 'To be assigned', // Required field, will be updated when member is onboarded
        };

        console.log(' Creating flat with data:', flatData);
        addDebugMessage(` Creating flat: ${flatData.flat_number}`, 'info');
        const createdFlat = await flatsService.createFlat(flatData);
        console.log(' Flat created successfully:', createdFlat);
        addDebugMessage(` Flat "${flatForm.flat_number.trim()}" created successfully!`, 'success');
        alert(`Flat "${flatForm.flat_number.trim()}" added successfully!`);
      }

      // Reload data and reset form
      await loadData();
      setFlatForm({
        flat_number: '',
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: '',
      });
    } catch (error) {
      console.error(' Error saving flat:', error);
      const errorDetails = {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url,
        requestData: error.config?.data
      };
      console.error('Error details:', errorDetails);
      addDebugMessage(` Error saving flat: ${error.message}`, 'error');
      if (error.response?.data) {
        addDebugMessage(`Response: ${JSON.stringify(error.response.data)}`, 'error');
      }
      const errorMsg = getErrorMessage(error) || 'Failed to save flat';
      if (Array.isArray(errorMsg)) {
        const validationErrors = errorMsg.map(e => typeof e === 'object' ? e.msg || e.message : e).join('\n');
        addDebugMessage(`Validation Errors: ${validationErrors}`, 'error');
        alert(`Validation Error:\n${validationErrors}`);
      } else {
        addDebugMessage(`Full Error: ${errorMsg}`, 'error');
        alert(`Error: ${errorMsg}\n\nCheck the Debug Panel below for details.`);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Flats & Blocks Setup</h2>
      <p className="settings-tab-description">Physical structure of the society</p>

      <div className="settings-section">
        <h3>Blocks / Wings</h3>
        <div style={{ marginBottom: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className="settings-add-btn"
            onClick={handleAddBlock}
            disabled={saving}
          >
            + Add Block
          </button>
          {blocksConfig.length > 0 && (
            <button
              className="settings-save-btn"
              onClick={() => handleSaveBlocksConfig()}
              disabled={saving}
              style={{ marginLeft: '10px' }}
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          )}
        </div>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Block/Wing</th>
                <th>Floors</th>
                <th>Flats per Floor</th>
                <th>Total Flats</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {blocksConfig.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
                    No blocks configured. Click "+ Add Block" to add one.
                  </td>
                </tr>
              ) : (
                blocksConfig.map((block, index) => {
                  const totalFlats = blockTotalFlats(block);
                  const isEditing = editingBlock === index;
                  return (
                    <tr key={index}>
                      <td>
                        {isEditing ? (
                          <input
                            type="text"
                            value={block.name}
                            onChange={(e) => handleUpdateBlock(index, 'name', e.target.value)}
                            style={{ width: '60px', padding: '4px' }}
                            maxLength="10"
                          />
                        ) : (
                          <strong>{block.name}</strong>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="number"
                            value={block.floors}
                            onChange={(e) => handleUpdateBlock(index, 'floors', parseInt(e.target.value) || 0)}
                            style={{ width: '80px', padding: '4px' }}
                            min="1"
                          />
                        ) : (
                          block.floors
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <button
                                type="button"
                                className="settings-action-btn"
                                style={{
                                  backgroundColor: block.customPerFloor ? '#f3f4f6' : '#007AFF',
                                  color: block.customPerFloor ? '#333' : 'white',
                                  borderColor: '#007AFF',
                                }}
                                onClick={() => handleUpdateBlock(index, 'customPerFloor', false)}
                              >
                                Uniform
                              </button>
                              <button
                                type="button"
                                className="settings-action-btn"
                                style={{
                                  backgroundColor: block.customPerFloor ? '#007AFF' : '#f3f4f6',
                                  color: block.customPerFloor ? 'white' : '#333',
                                  borderColor: '#007AFF',
                                }}
                                onClick={() => handleUpdateBlock(index, 'customPerFloor', true)}
                              >
                                Custom per floor
                              </button>
                            </div>
                            {!block.customPerFloor ? (
                              <input
                                type="number"
                                value={block.flatsPerFloor}
                                onChange={(e) => handleUpdateBlock(index, 'flatsPerFloor', parseInt(e.target.value, 10) || 0)}
                                style={{ width: '120px', padding: '4px' }}
                                min="1"
                              />
                            ) : (
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(84px, 1fr))', gap: '6px' }}>
                                {Array.from({ length: Math.max(1, parseInt(block.floors, 10) || 1) }).map((_, floorIdx) => (
                                  <label key={floorIdx} style={{ display: 'flex', flexDirection: 'column', fontSize: '12px', color: '#555' }}>
                                    Floor {floorIdx + 1}
                                    <input
                                      type="number"
                                      min="1"
                                      value={(block.flatsByFloor || [])[floorIdx] ?? block.flatsPerFloor}
                                      onChange={(e) => handleCustomFloorCountChange(index, floorIdx, e.target.value)}
                                      style={{ width: '100%', padding: '4px' }}
                                    />
                                  </label>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          block.customPerFloor && Array.isArray(block.flatsByFloor) && block.flatsByFloor.length > 0
                            ? `Custom (${block.flatsByFloor.join('/')})`
                            : `Uniform (${block.flatsPerFloor})`
                        )}
                      </td>
                      <td>
                        <strong>{totalFlats}</strong>
                      </td>
                      <td>
                        {isEditing ? (
                          <button
                            className="settings-action-btn"
                            onClick={() => handleSaveBlock(index)}
                            style={{ backgroundColor: '#34C759', color: 'white' }}
                          >
                             Save
                          </button>
                        ) : (
                          <>
                            <button
                              className="settings-action-btn"
                              onClick={() => handleEditBlock(index)}
                            >
                              Edit
                            </button>
                            <button
                              className="settings-action-btn danger"
                              onClick={() => handleDeleteBlock(index)}
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {blocksConfig.length > 0 && (
          <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '6px', fontSize: '14px', color: '#666' }}>
            <strong>Note:</strong> After saving, flats will be automatically synced to match this configuration.
            Existing flats that don't match will be removed, and missing flats will be created.
          </div>
        )}
      </div>

      <div className="settings-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Existing Flats</h3>
          <button
            onClick={loadData}
            disabled={loading}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007AFF',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        {loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            Loading flats and members data...
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '16px', fontSize: '14px', color: '#666' }}>
              {flats.length > 0 && (
                <span style={{ color: '#34C759', marginRight: '16px' }}>
                   {flats.length} flat{flats.length !== 1 ? 's' : ''} loaded
                </span>
              )}
              {members.length > 0 && (
                <span style={{ color: '#34C759' }}>
                   {members.length} member{members.length !== 1 ? 's' : ''} loaded
                </span>
              )}
              {flats.length === 0 && members.length === 0 && (
                <span style={{ color: '#FF9500' }}>
                   No data loaded. Check console for errors or click Refresh.
                </span>
              )}
            </div>

            {flats.length > 0 ? (
              <div className="settings-table-container" style={{ marginBottom: '24px' }}>
                {/* Debug Info */}
                {flats.some(f => (f.flat_number || f.flatNumber || '').trim().toUpperCase() === 'A-304') && (
                  <div style={{
                    padding: '10px',
                    marginBottom: '10px',
                    backgroundColor: '#FFF3CD',
                    border: '1px solid #FFC107',
                    borderRadius: '4px',
                    fontSize: '12px'
                  }}>
                    <strong>A-304 Debug:</strong> Members loaded: {members.length},
                    A-304 Member: {members.find(m => ((m.flat_number || m.flatNumber || '').trim().toUpperCase() === 'A-304'))?.name || 'NOT FOUND'}
                    <br />
                    Check browser console (F12) for detailed logs.
                  </div>
                )}
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Flat Number</th>
                      <th>Area (Sq.ft)</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Owner/Tenant</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flats.map(flat => {
                      const flatId = flat.id || flat._id;
                      const flatNumber = flat.flat_number || flat.flatNumber;
                      const flatArea = flat.area_sqft || flat.areaSqft;

                      // Find active member for this flat - use same logic as Members page
                      // Normalize flat numbers for comparison (trim whitespace, case-insensitive)
                      const normalizedFlatNumber = flatNumber ? flatNumber.trim().toUpperCase() : '';

                      // Find active member for this flat - try multiple matching strategies
                      let flatMember = null;

                      // Only try to find member if we have members loaded
                      if (members && members.length > 0) {
                        flatMember = members.find(m => {
                          // Strategy 1: Match by flat_number (normalized)
                          const memberFlatNumber = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
                          const flatNumberMatch = memberFlatNumber === normalizedFlatNumber;

                          // Strategy 2: Match by flat_id (if available)
                          const memberFlatId = m.flat_id ? String(m.flat_id) : null;
                          const flatIdStr = flatId ? String(flatId) : null;
                          const flatIdMatch = flatIdStr && memberFlatId && memberFlatId === flatIdStr;

                          // Status checks - be more lenient
                          const statusLower = (m.status || '').toLowerCase();
                          const isActive = statusLower === 'active';
                          const hasNoMoveOut = !m.move_out_date ||
                            m.move_out_date === null ||
                            m.move_out_date === '' ||
                            (m.move_out_date && new Date(m.move_out_date) > new Date());

                          // Match if either flat_number OR flat_id matches, and member is active
                          const matches = (flatNumberMatch || flatIdMatch) && isActive && hasNoMoveOut;

                          // Debug for A-304
                          if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                            console.log(' A-304 Member Lookup - Checking member:', {
                              memberName: m.name,
                              memberFlatNumber: memberFlatNumber,
                              normalizedFlatNumber: normalizedFlatNumber,
                              memberFlatId: memberFlatId,
                              flatId: flatIdStr,
                              flatNumberMatch: flatNumberMatch,
                              flatIdMatch: flatIdMatch,
                              status: m.status,
                              statusLower: statusLower,
                              isActive: isActive,
                              move_out_date: m.move_out_date,
                              hasNoMoveOut: hasNoMoveOut,
                              matches: matches
                            });
                          }

                          return matches;
                        });

                        // Debug for A-304 - final result
                        if ((normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') && !flatMember) {
                          console.log(' A-304 NO MEMBER FOUND - All members checked:', {
                            totalMembers: members.length,
                            allMembers: members.map(m => ({
                              name: m.name,
                              flat_number: m.flat_number || m.flatNumber,
                              flat_id: m.flat_id,
                              status: m.status,
                              move_out_date: m.move_out_date
                            })),
                            searchCriteria: {
                              normalizedFlatNumber: normalizedFlatNumber,
                              flatId: flatId
                            }
                          });
                        } else if ((normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') && flatMember) {
                          console.log(' A-304 MEMBER FOUND:', {
                            name: flatMember.name,
                            flat_number: flatMember.flat_number,
                            flat_id: flatMember.flat_id,
                            status: flatMember.status,
                            member_type: flatMember.member_type
                          });
                        }
                      } else {
                        // Debug: No members loaded
                        if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                          console.log(' A-304: Members array is empty or not loaded yet');
                        }
                      }

                      // Debug for A-304 specifically (console only, no state updates during render)
                      if (normalizedFlatNumber === 'A-304') {
                        console.log(' A-304 Debug:', {
                          flatNumber: flatNumber,
                          normalizedFlatNumber: normalizedFlatNumber,
                          membersCount: members.length,
                          matchingMembers: members.filter(m => {
                            const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
                            return mFlat === normalizedFlatNumber;
                          }),
                          foundMember: flatMember,
                          allMembersForA304: members.filter(m => {
                            const mFlat = (m.flat_number || m.flatNumber || '').trim();
                            return mFlat.toUpperCase().includes('A-304');
                          })
                        });
                        // Note: Don't call addDebugMessage here - it updates state and causes infinite loop
                        // Use console.log only for debugging during render
                      }

                      return (
                        <tr key={flatId || flatNumber}>
                          <td><strong>{flatNumber}</strong></td>
                          <td>
                            <input
                              type="number"
                              value={flatArea || ''}
                              onChange={async (e) => {
                                const newArea = parseFloat(e.target.value);
                                if (!isNaN(newArea) && newArea > 0 && flatId) {
                                  try {
                                    await flatsService.updateFlat(flatId, { area_sqft: newArea });
                                    addDebugMessage(` Updated area for ${flatNumber} to ${newArea}`, 'success');
                                    await loadData(); // Reload to refresh the list
                                  } catch (error) {
                                    console.error('Error updating area:', error);
                                    addDebugMessage(` Error updating area: ${error.message}`, 'error');
                                    alert('Failed to update area. Please try again.');
                                  }
                                }
                              }}
                              onBlur={async (e) => {
                                // Auto-save on blur if value changed
                                const newArea = parseFloat(e.target.value);
                                if (!isNaN(newArea) && newArea > 0 && flatId && newArea !== flatArea) {
                                  try {
                                    await flatsService.updateFlat(flatId, { area_sqft: newArea });
                                    addDebugMessage(` Auto-saved area for ${flatNumber}`, 'success');
                                    await loadData();
                                  } catch (error) {
                                    console.error('Error auto-saving area:', error);
                                  }
                                }
                              }}
                              style={{
                                width: '100px',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                border: '1px solid #ddd',
                                fontSize: '14px',
                              }}
                              placeholder="Area"
                            />
                          </td>
                          <td>{flat.bedrooms ? `${flat.bedrooms} BR` : 'N/A'}</td>
                          <td>
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: '600',
                              backgroundColor: flatMember
                                ? (((flatMember.member_type || flatMember.memberType || '').toLowerCase() === 'owner') ? '#E3F2FD' : '#E8F5E9')
                                : '#F5F5F5',
                              color: flatMember
                                ? (((flatMember.member_type || flatMember.memberType || '').toLowerCase() === 'owner') ? '#1976D2' : '#2E7D32')
                                : '#666',
                            }}>
                              {(() => {
                                if (!flatMember) {
                                  if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                                    console.log(' A-304 Showing Vacant:', { flatId, flatNumber, membersCount: members.length });
                                  }
                                  return 'Vacant';
                                }
                                const memberType = (flatMember.member_type || flatMember.memberType || 'owner').toLowerCase();
                                return memberType === 'owner' ? 'Owner' : 'Tenant';
                              })()}
                            </span>
                          </td>
                          <td>
                            {flatMember ? flatMember.name : (flat.owner_name || 'N/A')}
                            {normalizedFlatNumber === 'A-304' && flatMember && console.log(' A-304 Found:', flatMember.name)}
                          </td>
                          <td>
                            <button
                              className="settings-action-btn"
                              onClick={() => {
                                // Auto-fill form with this flat's data
                                handleFlatNumberChange(flat.flat_number);
                                // Scroll to form
                                document.querySelector('.settings-section:last-child')?.scrollIntoView({ behavior: 'smooth' });
                              }}
                            >
                              Edit
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#666', marginBottom: '24px' }}>
                No flats found. Add your first flat below.
              </div>
            )}
          </>
        )}
      </div>

      <div className="settings-section">
        <h3>Add / Edit Flat Details</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleAddFlat(e);
          }}
          style={{ display: 'contents' }}
        >
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Flat Number *</label>
              <input
                type="text"
                placeholder="A-101"
                value={flatForm.flat_number}
                onChange={(e) => handleFlatNumberChange(e.target.value)}
                list="flat-numbers"
              />
              <datalist id="flat-numbers">
                {flats.map(flat => (
                  <option key={flat.id || flat._id || flat.flat_number} value={flat.flat_number || flat.flatNumber} />
                ))}
              </datalist>
              <small style={{ color: '#666', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                Start typing to see existing flats. Data will auto-fill from member records.
              </small>
            </div>
            <div className="settings-form-group">
              <label>Flat Size (Sq.ft) *</label>
              <input
                type="number"
                placeholder="1200"
                value={flatForm.area_sqft}
                onChange={(e) => setFlatForm(prev => ({ ...prev, area_sqft: e.target.value }))}
              />
            </div>
            <div className="settings-form-group">
              <label>Flat Type</label>
              <select
                value={flatForm.flat_type}
                onChange={(e) => setFlatForm(prev => ({ ...prev, flat_type: e.target.value }))}
              >
                <option value="">Select Type</option>
                <option>1 BHK</option>
                <option>2 BHK</option>
                <option>3 BHK</option>
                <option>4 BHK</option>
                <option>Penthouse</option>
              </select>
            </div>
            <div className="settings-form-group">
              <label>Status</label>
              <select
                value={flatForm.status}
                onChange={(e) => setFlatForm(prev => ({ ...prev, status: e.target.value }))}
              >
                <option>Owner Occupied</option>
                <option>Tenant</option>
                <option>Vacant</option>
              </select>
            </div>
          </div>
          <div className="settings-form-group">
            <label>Parking Slots</label>
            <input
              type="text"
              placeholder="P-01, P-02"
              value={flatForm.parking_slots}
              onChange={(e) => setFlatForm(prev => ({ ...prev, parking_slots: e.target.value }))}
            />
          </div>
          <div style={{ marginTop: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              type="submit"
              className="settings-add-btn"
              disabled={loading || saving}
              style={{
                opacity: (loading || saving) ? 0.6 : 1,
                cursor: (loading || saving) ? 'not-allowed' : 'pointer',
                padding: '12px 24px',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              {saving ? ' Saving...' : `+ ${flats.find(f => f.flat_number === flatForm.flat_number.trim()) ? 'Update' : 'Add'} Flat`}
            </button>
            <button
              type="button"
              onClick={() => {
                alert('Test button works! Now try the Add Flat button.');
                addDebugMessage(' Test button clicked', 'info');
              }}
              style={{
                padding: '12px 24px',
                backgroundColor: '#34C759',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 'bold'
              }}
            >
               Test Click
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FlatsBlocksTab;
