import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import meetingService from '../services/meetingService';
import { authService } from '../services/authService';
import messagesService from '../services/messagesService';

const MeetingsScreen = () => {
    const navigate = useNavigate();
    const [meetings, setMeetings] = useState([]);
    const [selectedMeeting, setSelectedMeeting] = useState(null);
    const [meetingDetails, setMeetingDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadingDetails, setLoadingDetails] = useState(false);
    const [user, setUser] = useState(null);

    // Modals
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showAttendanceModal, setShowAttendanceModal] = useState(false);
    const [showMinutesModal, setShowMinutesModal] = useState(false);
    const [showResolutionModal, setShowResolutionModal] = useState(false);

    // Form States
    const [newMeeting, setNewMeeting] = useState({
        meeting_title: '',
        meeting_type: 'MC',
        meeting_date: new Date().toISOString().split('T')[0],
        meeting_time: '10:00 AM',
        venue: '',
        notice_sent_to: 'all_members',
        notice_room_id: '',
        eligible_member_ids: []
    });

    const [editMeeting, setEditMeeting] = useState(null);

    const [agendaItems, setAgendaItems] = useState([{ item_number: 1, item_title: '', item_description: '' }]);
    const [minutesText, setMinutesText] = useState('');
    const [members, setMembers] = useState([]);
    const [noticeRooms, setNoticeRooms] = useState([]);
    const [attendance, setAttendance] = useState({}); // { memberId: 'present' | 'absent' | 'proxy' }
    const normalizedRole = String(user?.role || '').toLowerCase();
    const canManageMeetings = !['resident', 'member', 'tenant'].includes(normalizedRole);
    const selectedEligibleMembers = members.filter(member => newMeeting.eligible_member_ids.includes(member.id));

    const [newResolution, setNewResolution] = useState({
        resolution_title: '',
        resolution_text: '',
        resolution_type: 'ordinary',
        proposed_by_id: '',
        seconded_by_id: '',
        votes_for: 0,
        votes_against: 0,
        votes_abstain: 0,
        result: 'passed'
    });

    useEffect(() => {
        const init = async () => {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
            loadMeetings();
            loadMembers();
            loadNoticeRooms();
        };
        init();
    }, []);

    useEffect(() => {
        if (selectedMeeting) {
            loadMeetingDetails(selectedMeeting.id);
        }
    }, [selectedMeeting]);

    const loadMeetings = async (autoSelectId = null) => {
        setLoading(true);
        try {
            const data = await meetingService.getMeetings();
            setMeetings(data);
            if (autoSelectId) {
                const found = data.find(m => m.id === autoSelectId);
                if (found) setSelectedMeeting(found);
            } else if (!selectedMeeting && data.length > 0) {
                setSelectedMeeting(data[0]);
            }
        } catch (error) {
            console.error('Error loading meetings:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadMembers = async () => {
        try {
            const data = await meetingService.getMembers();
            setMembers(data);
        } catch (error) {
            console.error('Error loading members:', error);
        }
    };

    const loadNoticeRooms = async () => {
        try {
            const rooms = await messagesService.listRooms();
            setNoticeRooms(Array.isArray(rooms) ? rooms : []);
        } catch (error) {
            console.error('Error loading notice rooms:', error);
        }
    };

    const toggleEligibleMember = (memberId) => {
        const selected = newMeeting.eligible_member_ids || [];
        setNewMeeting({
            ...newMeeting,
            eligible_member_ids: selected.includes(memberId)
                ? selected.filter(id => id !== memberId)
                : [...selected, memberId]
        });
    };

    const toggleEditEligibleMember = (memberId) => {
        const selected = editMeeting?.eligible_member_ids || [];
        setEditMeeting({
            ...editMeeting,
            eligible_member_ids: selected.includes(memberId)
                ? selected.filter(id => id !== memberId)
                : [...selected, memberId]
        });
    };

    const meetingEligibleMembers = meetingDetails?.meeting?.eligible_member_ids?.length
        ? members.filter(member => meetingDetails.meeting.eligible_member_ids.includes(member.id))
        : members;

    const loadMeetingDetails = async (meetingId) => {
        setLoadingDetails(true);
        try {
            const details = await meetingService.getMeetingDetails(meetingId);
            setMeetingDetails(details);
            setMinutesText(details.meeting.minutes_text || '');

            // Initialize attendance state from details
            const attendanceMap = {};
            details.attendance.forEach(record => {
                attendanceMap[record.member_id] = record.status;
            });
            setAttendance(attendanceMap);
        } catch (error) {
            console.error('Error loading meeting details:', error);
        } finally {
            setLoadingDetails(false);
        }
    };

    const handleCreateMeeting = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                ...newMeeting,
                agenda_items: agendaItems.filter(item => item.item_title.trim() !== '')
            };
            const created = await meetingService.createMeeting(payload);
            setShowCreateModal(false);
            setNewMeeting({
                meeting_title: '',
                meeting_type: 'MC',
                meeting_date: new Date().toISOString().split('T')[0],
                meeting_time: '10:00 AM',
                venue: '',
                notice_sent_to: 'all_members',
                notice_room_id: '',
                eligible_member_ids: []
            });
            setAgendaItems([{ item_number: 1, item_title: '', item_description: '' }]);
            loadMeetings(created.id);
        } catch (error) {
            console.error('Error creating meeting:', error);
            alert('Failed to create meeting');
        }
    };

    const handleEditMeeting = async (e) => {
        e.preventDefault();
        try {
            const action = String(editMeeting.change_action || 'general_update');
            const reason = String(editMeeting.change_reason || '').trim();
            if (['cancel', 'postpone', 'prepone'].includes(action) && !reason) {
                alert('Reason is required for cancel/postpone/prepone.');
                return;
            }
            const payload = {
                ...editMeeting,
                change_action: action,
                change_reason: reason || undefined,
            };
            if (action === 'cancel') {
                payload.status = 'CANCELLED';
            }
            await meetingService.updateMeeting(selectedMeeting.id, payload);
            setShowEditModal(false);
            loadMeetings(selectedMeeting.id);
            loadMeetingDetails(selectedMeeting.id);
        } catch (error) {
            console.error('Error updating meeting:', error);
            alert('Failed to update meeting');
        }
    };

    const handleSendNotice = async () => {
        if (!selectedMeeting) return;
        const roomName = meetingDetails?.meeting?.notice_room_name
            || noticeRooms.find(room => room.id === meetingDetails?.meeting?.notice_room_id)?.name
            || 'Meeting Notices';
        if (!window.confirm(`Post meeting notice to ${roomName}?`)) return;

        try {
            const result = await meetingService.sendNotice(selectedMeeting.id, {
                send_email: false,
                send_sms: false,
                room_id: meetingDetails?.meeting?.notice_room_id || undefined
            });
            const eligibleCount = result?.eligible_members ?? meetingDetails?.meeting?.total_members_eligible ?? 0;
            const postedRoom = result?.message_room?.name || roomName;
            alert(`Notice posted to ${postedRoom} for ${eligibleCount} eligible members.`);
            loadMeetingDetails(selectedMeeting.id);
        } catch (error) {
            console.error('Error sending notice:', error);
            alert('Failed to post notice');
        }
    };

    const handleSaveAttendance = async () => {
        try {
            const attendees = Object.entries(attendance).map(([id, status]) => ({
                member_id: String(id),
                status
            }));
            await meetingService.markAttendance(selectedMeeting.id, { attendees });
            setShowAttendanceModal(false);
            loadMeetingDetails(selectedMeeting.id);
        } catch (error) {
            console.error('Error saving attendance:', error);
            alert('Failed to save attendance');
        }
    };

    const handleSaveMinutes = async () => {
        try {
            await meetingService.recordMinutes(selectedMeeting.id, { minutes_text: minutesText });
            setShowMinutesModal(false);
            loadMeetingDetails(selectedMeeting.id);
        } catch (error) {
            console.error('Error saving minutes:', error);
            alert('Failed to save minutes');
        }
    };

    const handleCreateResolution = async (e) => {
        e.preventDefault();
        try {
            const safeParseInt = (val) => {
                const parsed = parseInt(val);
                return isNaN(parsed) ? 0 : parsed;
            };

            const payload = {
                ...newResolution,
                proposed_by_id: String(newResolution.proposed_by_id || ''),
                seconded_by_id: String(newResolution.seconded_by_id || ''),
                votes_for: safeParseInt(newResolution.votes_for),
                votes_against: safeParseInt(newResolution.votes_against),
                votes_abstain: safeParseInt(newResolution.votes_abstain)
            };
            await meetingService.createResolution(selectedMeeting.id, payload);
            setShowResolutionModal(false);
            setNewResolution({
                resolution_title: '',
                resolution_text: '',
                resolution_type: 'ordinary',
                proposed_by_id: '',
                seconded_by_id: '',
                votes_for: 0,
                votes_against: 0,
                votes_abstain: 0,
                result: 'passed'
            });
            loadMeetingDetails(selectedMeeting.id);
        } catch (error) {
            console.error('Error creating resolution:', error);
            alert('Failed to create resolution');
        }
    };

    const getStatusColor = (status) => {
        switch (status?.toLowerCase()) {
            case 'scheduled': return '#E6A800';
            case 'completed': return '#2E8B57';
            case 'cancelled': return '#C0392B';
            default: return '#8E8E93';
        }
    };

    const presentCount = meetingDetails
        ? (meetingDetails.meeting?.total_members_present ??
            (meetingDetails.attendance || []).filter(a => ['present', 'proxy'].includes(String(a?.status || '').toLowerCase())).length)
        : 0;

    if (loading && meetings.length === 0) {
        return (
            <div className="loading-container">
                <div className="loading-text">Loading meetings...</div>
            </div>
        );
    }

    return (
        <div className="dashboard-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="dashboard-header" style={{ flexShrink: 0 }}>
                <div className="dashboard-header-left">
                    <h1 className="dashboard-header-title"> Meetings</h1>
                    <span className="dashboard-header-subtitle">Schedule & Minutes</span>
                </div>
                <div className="dashboard-header-right">
                    {canManageMeetings && (
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="dashboard-logout-button"
                            style={{
                                backgroundColor: '#fff',
                                color: '#8A3E00',
                                border: '1px solid rgba(255,255,255,0.45)',
                                marginRight: '12px'
                            }}
                        >
                            + Schedule Meeting
                        </button>
                    )}
                    <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
                         Back to Dashboard
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: '24px', gap: '24px' }}>
                {/* Sidebar - Meetings List */}
                <div style={{
                    width: '350px',
                    backgroundColor: 'white',
                    borderRadius: '16px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    border: '1px solid #f0f0f0'
                }}>
                    <div style={{
                        padding: '24px',
                        borderBottom: '1px solid #f0f0f0',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'linear-gradient(to bottom, #fff, #fafafa)'
                    }}>
                        <span style={{ fontWeight: '700', color: '#1D1D1F', fontSize: '18px' }}>Meetings</span>
                        {canManageMeetings && (
                            <button
                                onClick={() => setShowCreateModal(true)}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '10px',
                                    backgroundColor: '#E8842A',
                                    color: 'white',
                                    border: 'none',
                                    fontSize: '13px',
                                    cursor: 'pointer',
                                    fontWeight: '700',
                                    boxShadow: '0 4px 10px rgba(232, 132, 42, 0.2)'
                                }}
                            >
                                + Schedule
                            </button>
                        )}
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
                        {meetings.length === 0 ? (
                            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#8E8E93' }}>
                                <div>No meetings scheduled yet.</div>
                                {canManageMeetings && (
                                    <button
                                        onClick={() => setShowCreateModal(true)}
                                        style={{
                                            marginTop: '18px',
                                            padding: '10px 16px',
                                            borderRadius: '10px',
                                            backgroundColor: '#E8842A',
                                            color: 'white',
                                            border: 'none',
                                            fontSize: '13px',
                                            cursor: 'pointer',
                                            fontWeight: '700'
                                        }}
                                    >
                                        + Schedule Meeting
                                    </button>
                                )}
                            </div>
                        ) : (
                            meetings.map(meeting => (
                                <div
                                    key={meeting.id}
                                    onClick={() => setSelectedMeeting(meeting)}
                                    style={{
                                        padding: '16px',
                                        cursor: 'pointer',
                                        borderRadius: '12px',
                                        marginBottom: '8px',
                                        backgroundColor: selectedMeeting?.id === meeting.id ? '#FFF7EC' : 'transparent',
                                        border: selectedMeeting?.id === meeting.id ? '1px solid #F4A640' : '1px solid transparent',
                                        transition: 'all 0.2s',
                                        position: 'relative'
                                    }}
                                >
                                    <div style={{ fontWeight: '700', fontSize: '15px', color: '#1D1D1F', marginBottom: '6px' }}>
                                        {meeting.meeting_title}
                                    </div>
                                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px' }}>
                                        <span style={{
                                            fontSize: '10px',
                                            fontWeight: '800',
                                            padding: '2px 6px',
                                            backgroundColor: '#f0f0f0',
                                            borderRadius: '4px',
                                            color: '#666'
                                        }}>{meeting.meeting_type}</span>
                                        <span style={{ fontSize: '12px', color: '#8E8E93' }}>{meeting.meeting_date}</span>
                                    </div>
                                    <div style={{
                                        fontSize: '11px',
                                        fontWeight: '700',
                                        color: getStatusColor(meeting.status),
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.5px'
                                    }}>
                                         {meeting.status}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Main Content Area */}
                <div style={{
                    flex: 1,
                    backgroundColor: 'white',
                    borderRadius: '16px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    border: '1px solid #f0f0f0'
                }}>
                    {!selectedMeeting ? (
                        <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#8E8E93', backgroundColor: '#fafafa' }}>
                            <span style={{ fontSize: '64px', marginBottom: '20px' }}></span>
                            <span style={{ fontSize: '18px', fontWeight: '600' }}>Select a meeting to view details</span>
                        </div>
                    ) : (
                        loadingDetails || !meetingDetails ? (
                            <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center' }}>
                                <div className="loading-text">{loadingDetails ? 'Loading details...' : 'Preparing details...'}</div>
                            </div>
                        ) : (
                            <>
                                {/* Meeting Detail Header */}
                                <div style={{
                                    padding: '30px',
                                    borderBottom: '1px solid #f0f0f0',
                                    background: 'linear-gradient(to right, #fff, #fdfdfd)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'flex-start'
                                }}>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                                            <span style={{
                                                fontSize: '12px',
                                                fontWeight: '800',
                                                padding: '4px 10px',
                                                backgroundColor: '#FFF7EC',
                                                color: '#E8842A',
                                                borderRadius: '6px',
                                                border: '1px solid #F4A640'
                                            }}>{meetingDetails.meeting.meeting_type}</span>
                                            <div style={{
                                                fontSize: '12px',
                                                fontWeight: '700',
                                                color: getStatusColor(meetingDetails.meeting.status),
                                                backgroundColor: getStatusColor(meetingDetails.meeting.status) + '15',
                                                padding: '4px 10px',
                                                borderRadius: '6px',
                                                textTransform: 'uppercase'
                                            }}>
                                                {meetingDetails.meeting.status}
                                            </div>
                                        </div>
                                        <h2 style={{ fontSize: '28px', color: '#1D1D1F', marginBottom: '12px' }}>{meetingDetails.meeting.meeting_title}</h2>
                                        <div style={{ display: 'flex', gap: '24px', color: '#5A2E0A', fontSize: '15px', fontWeight: '500' }}>
                                            <span> {meetingDetails.meeting.meeting_date}</span>
                                            <span> {meetingDetails.meeting.meeting_time || 'N/A'}</span>
                                            <span> {meetingDetails.meeting.venue || 'No venue specified'}</span>
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        {canManageMeetings && (
                                            <>
                                                {!meetingDetails.meeting.notice_sent && (
                                                    <button onClick={handleSendNotice} style={{
                                                        padding: '10px 20px',
                                                        borderRadius: '10px',
                                                        backgroundColor: '#007AFF',
                                                        color: 'white',
                                                        border: 'none',
                                                        fontSize: '14px',
                                                        fontWeight: '700',
                                                        cursor: 'pointer'
                                                    }}>
                                                        Send Notice
                                                    </button>
                                                )}
                                                <button onClick={() => {
                                                    setEditMeeting({
                                                        meeting_title: meetingDetails.meeting.meeting_title,
                                                        meeting_type: meetingDetails.meeting.meeting_type,
                                                        meeting_date: meetingDetails.meeting.meeting_date,
                                                        meeting_time: meetingDetails.meeting.meeting_time,
                                                        venue: meetingDetails.meeting.venue,
                                                        notice_room_id: meetingDetails.meeting.notice_room_id || '',
                                                        eligible_member_ids: meetingDetails.meeting.eligible_member_ids || [],
                                                        status: meetingDetails.meeting.status,
                                                        total_members_eligible: meetingDetails.meeting.total_members_eligible || 0,
                                                        quorum_required: meetingDetails.meeting.quorum_required || 0,
                                                        quorum_met: meetingDetails.meeting.quorum_met,
                                                        change_action: 'general_update',
                                                        change_reason: '',
                                                    });
                                                    setShowEditModal(true);
                                                }} style={{
                                                    padding: '10px 20px',
                                                    borderRadius: '10px',
                                                    backgroundColor: 'white',
                                                    color: '#E8842A',
                                                    border: '1px solid #E8842A',
                                                    fontSize: '14px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer'
                                                }}>
                                                    Edit
                                                </button>
                                                <button onClick={() => setShowAttendanceModal(true)} style={{
                                                    padding: '10px 20px',
                                                    borderRadius: '10px',
                                                    backgroundColor: 'white',
                                                    color: '#007AFF',
                                                    border: '1px solid #007AFF',
                                                    fontSize: '14px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer'
                                                }}>
                                                    Attendance
                                                </button>
                                                <button onClick={() => setShowMinutesModal(true)} style={{
                                                    padding: '10px 20px',
                                                    borderRadius: '10px',
                                                    backgroundColor: 'white',
                                                    color: '#2E8B57',
                                                    border: '1px solid #2E8B57',
                                                    fontSize: '14px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer'
                                                }}>
                                                    Record Minutes
                                                </button>
                                                <button onClick={() => setShowResolutionModal(true)} style={{
                                                    padding: '10px 20px',
                                                    borderRadius: '10px',
                                                    backgroundColor: 'white',
                                                    color: '#6A5ACD',
                                                    border: '1px solid #6A5ACD',
                                                    fontSize: '14px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer'
                                                }}>
                                                    Add Resolution
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Meeting Details Content */}
                                <div style={{ flex: 1, overflowY: 'auto', padding: '30px', backgroundColor: '#f9f9fb' }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
                                        {/* Left Column - Agenda & Minutes */}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                                            <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '12px', border: '1px solid #f0f0f0' }}>
                                                <h3 style={{ fontSize: '18px', color: '#1D1D1F', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                     Agenda Items
                                                </h3>
                                                {meetingDetails.meeting.agenda && (
                                                    <div style={{
                                                        marginBottom: '20px',
                                                        padding: '16px',
                                                        backgroundColor: '#FFF7EC',
                                                        borderRadius: '8px',
                                                        borderLeft: '4px solid #F4A640',
                                                        fontSize: '14px',
                                                        color: '#5A2E0A'
                                                    }}>
                                                        <strong>Note:</strong> {meetingDetails.meeting.agenda}
                                                    </div>
                                                )}
                                                {meetingDetails.agenda_items.length === 0 ? (
                                                    !meetingDetails.meeting.agenda && <p style={{ color: '#8E8E93', fontSize: '14px' }}>No agenda items listed.</p>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                                        {meetingDetails.agenda_items.map((item, idx) => (
                                                            <div key={item.id} style={{ display: 'flex', gap: '15px' }}>
                                                                <span style={{
                                                                    width: '24px',
                                                                    height: '24px',
                                                                    backgroundColor: '#FFF7EC',
                                                                    color: '#E8842A',
                                                                    borderRadius: '50%',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'center',
                                                                    fontSize: '12px',
                                                                    fontWeight: '800',
                                                                    flexShrink: 0
                                                                }}>{idx + 1}</span>
                                                                <div>
                                                                    <div style={{ fontWeight: '700', color: '#1D1D1F', fontSize: '15px' }}>{item.item_title}</div>
                                                                    {item.item_description && (
                                                                        <div style={{ fontSize: '14px', color: '#5A2E0A', marginTop: '4px', lineHeight: '1.5' }}>{item.item_description}</div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>

                                            <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '12px', border: '1px solid #f0f0f0' }}>
                                                <h3 style={{ fontSize: '18px', color: '#1D1D1F', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                     Meeting Minutes
                                                </h3>
                                                {meetingDetails.meeting.minutes_text ? (
                                                    <div style={{
                                                        whiteSpace: 'pre-wrap',
                                                        fontSize: '15px',
                                                        color: '#5A2E0A',
                                                        lineHeight: '1.6',
                                                        padding: '16px',
                                                        backgroundColor: '#fafafa',
                                                        borderRadius: '8px',
                                                        border: '1px dashed #ddd'
                                                    }}>
                                                        {meetingDetails.meeting.minutes_text}
                                                    </div>
                                                ) : (
                                                    <div style={{ padding: '40px', textAlign: 'center', border: '2px dashed #eee', borderRadius: '12px' }}>
                                                        <span style={{ fontSize: '32px', display: 'block', marginBottom: '10px' }}></span>
                                                        <p style={{ color: '#8E8E93', fontSize: '14px' }}>Minutes haven't been recorded yet.</p>
                                                        {canManageMeetings && (
                                                            <button onClick={() => setShowMinutesModal(true)} style={{
                                                                marginTop: '15px',
                                                                padding: '8px 16px',
                                                                backgroundColor: 'white',
                                                                border: '1px solid #E8842A',
                                                                color: '#E8842A',
                                                                borderRadius: '8px',
                                                                fontSize: '13px',
                                                                fontWeight: '600',
                                                                cursor: 'pointer'
                                                            }}>Start Recording</button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Right Column - Stats & Attendance */}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                                            <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '12px', border: '1px solid #f0f0f0' }}>
                                                <h3 style={{ fontSize: '18px', color: '#1D1D1F', marginBottom: '20px' }}>Statistics</h3>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                                                        <span style={{ color: '#8E8E93' }}>Eligible Members:</span>
                                                        <span style={{ fontWeight: '700', color: '#1D1D1F' }}>{meetingDetails.meeting.total_members_eligible ?? 0}</span>
                                                    </div>
                                                    {meetingDetails.meeting.eligible_member_ids?.length > 0 && (
                                                        <div style={{ fontSize: '12px', color: '#8E8E93', lineHeight: '1.5' }}>
                                                            {meetingEligibleMembers.map(member => `${member.name} (${member.flat_number || 'No flat'})`).join(', ')}
                                                        </div>
                                                    )}
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                                                        <span style={{ color: '#8E8E93' }}>Quorum Required:</span>
                                                        <span style={{ fontWeight: '700', color: '#1D1D1F' }}>{meetingDetails.meeting.quorum_required ?? 0}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                                                        <span style={{ color: '#8E8E93' }}>Present:</span>
                                                        <span style={{ fontWeight: '700', color: '#2E8B57' }}>{presentCount}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                                                        <span style={{ color: '#8E8E93' }}>Quorum Met:</span>
                                                        <span style={{
                                                            fontWeight: '700',
                                                            color: meetingDetails.meeting.quorum_met ? '#2E8B57' : '#C0392B'
                                                        }}>{meetingDetails.meeting.quorum_met ? 'YES' : 'NO'}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                                                        <span style={{ color: '#8E8E93' }}>Notice Sent:</span>
                                                        <span style={{
                                                            fontWeight: '700',
                                                            color: meetingDetails.meeting.notice_sent ? '#2E8B57' : '#E6A800'
                                                        }}>{meetingDetails.meeting.notice_sent ? 'SENT' : 'NOT SENT'}</span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '12px', border: '1px solid #f0f0f0' }}>
                                                <h3 style={{ fontSize: '18px', color: '#1D1D1F', marginBottom: '20px' }}>Resolutions</h3>
                                                {meetingDetails.resolutions.length === 0 ? (
                                                    <p style={{ color: '#8E8E93', fontSize: '14px' }}>No recorded resolutions.</p>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                        {meetingDetails.resolutions.map(res => (
                                                            <div key={res.id} style={{
                                                                padding: '12px',
                                                                backgroundColor: '#f8f9fa',
                                                                borderRadius: '8px',
                                                                borderLeft: '4px solid #007AFF'
                                                            }}>
                                                                <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>{res.resolution_number}</div>
                                                                <div style={{ fontWeight: '700', fontSize: '14px', color: '#1D1D1F' }}>{res.resolution_title}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )
                    )}
                </div>
            </div>

            {/* Modals Implementation */}
            {/* Create Meeting Modal */}
            {showCreateModal && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '20px', width: '100%', maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 10px 40px rgba(0,0,0,0.3)' }}>
                        <div style={{ padding: '30px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h2 style={{ fontSize: '24px', fontWeight: '800', color: '#1D1D1F' }}>Schedule Society Meeting</h2>
                            <button onClick={() => setShowCreateModal(false)} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#8E8E93' }}></button>
                        </div>
                        <form onSubmit={handleCreateMeeting} style={{ padding: '30px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                                <div className="settings-form-group">
                                    <label>Meeting Title *</label>
                                    <input type="text" required value={newMeeting.meeting_title} onChange={e => setNewMeeting({ ...newMeeting, meeting_title: e.target.value })} placeholder="e.g. Monthly Committee Meeting" />
                                </div>
                                <div className="settings-form-group">
                                    <label>Meeting Type</label>
                                    <select value={newMeeting.meeting_type} onChange={e => setNewMeeting({ ...newMeeting, meeting_type: e.target.value })}>
                                        <option value="MC">Management Committee (MC)</option>
                                        <option value="AGM">Annual General Meeting (AGM)</option>
                                        <option value="EGM">Extraordinary General Meeting (EGM)</option>
                                        <option value="SGM">Special General Meeting (SGM)</option>
                                    </select>
                                </div>
                                <div className="settings-form-group">
                                    <label>Date *</label>
                                    <input type="date" required value={newMeeting.meeting_date} onChange={e => setNewMeeting({ ...newMeeting, meeting_date: e.target.value })} />
                                </div>
                                <div className="settings-form-group">
                                    <label>Time</label>
                                    <input type="text" value={newMeeting.meeting_time} onChange={e => setNewMeeting({ ...newMeeting, meeting_time: e.target.value })} placeholder="10:30 AM" />
                                </div>
                                <div className="settings-form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>Venue</label>
                                    <input type="text" value={newMeeting.venue} onChange={e => setNewMeeting({ ...newMeeting, venue: e.target.value })} placeholder="Clubhouse / Virtual / etc." />
                                </div>
                                <div className="settings-form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>Notice Room</label>
                                    <select value={newMeeting.notice_room_id} onChange={e => setNewMeeting({ ...newMeeting, notice_room_id: e.target.value })}>
                                        <option value="">Auto-create from eligible members</option>
                                        {noticeRooms.map(room => (
                                            <option key={room.id} value={room.id}>
                                                {room.name}{room.audience_type === 'flats' ? ` (${room.allowed_flat_numbers?.length || 0} flats)` : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="settings-form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>Eligible Members ({selectedEligibleMembers.length} selected)</label>
                                    <div style={{
                                        border: '1px solid #E5E5EA',
                                        borderRadius: '10px',
                                        padding: '12px',
                                        maxHeight: '220px',
                                        overflowY: 'auto',
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                                        gap: '8px'
                                    }}>
                                        {members.length === 0 ? (
                                            <div style={{ color: '#8E8E93', fontSize: '13px' }}>No members found. Add members first.</div>
                                        ) : (
                                            members.map(member => (
                                                <label key={member.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#1D1D1F' }}>
                                                    <input
                                                        type="checkbox"
                                                        checked={newMeeting.eligible_member_ids.includes(member.id)}
                                                        onChange={() => toggleEligibleMember(member.id)}
                                                    />
                                                    <span>
                                                        <strong>{member.name}</strong> ({member.flat_number || 'No flat'})
                                                        {member.member_type ? ` · ${member.member_type}` : ''}
                                                    </span>
                                                </label>
                                            ))
                                        )}
                                    </div>
                                    <div style={{ color: '#8E8E93', fontSize: '12px', marginTop: '6px' }}>
                                        Select MC members for MC meetings. If none are selected, the system treats all active members as eligible.
                                    </div>
                                </div>
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                                    <label style={{ fontWeight: '700', fontSize: '16px' }}>Agenda Items</label>
                                    <button type="button" onClick={() => setAgendaItems([...agendaItems, { item_number: agendaItems.length + 1, item_title: '', item_description: '' }])} style={{ background: 'none', border: 'none', color: '#007AFF', fontSize: '13px', fontWeight: '700', cursor: 'pointer' }}>+ Add Item</button>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                                    {agendaItems.map((item, idx) => (
                                        <div key={idx} style={{ padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '12px' }}>
                                            <div className="settings-form-group" style={{ marginBottom: '10px' }}>
                                                <input type="text" placeholder={`Agenda #${idx + 1} Title`} value={item.item_title} onChange={e => {
                                                    const updated = [...agendaItems];
                                                    updated[idx].item_title = e.target.value;
                                                    setAgendaItems(updated);
                                                }} />
                                            </div>
                                            <div className="settings-form-group">
                                                <textarea placeholder="Description (Optional)" rows="2" value={item.item_description} onChange={e => {
                                                    const updated = [...agendaItems];
                                                    updated[idx].item_description = e.target.value;
                                                    setAgendaItems(updated);
                                                }}></textarea>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end', marginTop: '40px' }}>
                                <button type="button" onClick={() => setShowCreateModal(false)} className="settings-cancel-btn">Cancel</button>
                                <button type="submit" className="settings-save-btn">Schedule Meeting</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Meeting Modal */}
            {showEditModal && editMeeting && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '20px', width: '100%', maxWidth: '600px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 40px rgba(0,0,0,0.3)', overflow: 'hidden' }}>
                        <div style={{ padding: '30px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h2 style={{ fontSize: '24px', fontWeight: '800' }}>Edit Meeting Details</h2>
                            <button onClick={() => setShowEditModal(false)} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#8E8E93' }}></button>
                        </div>
                        <form onSubmit={handleEditMeeting} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                            <div style={{ padding: '30px', overflowY: 'auto', display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
                                <div className="settings-form-group">
                                    <label>Meeting Title</label>
                                    <input type="text" value={editMeeting.meeting_title} onChange={e => setEditMeeting({ ...editMeeting, meeting_title: e.target.value })} />
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                    <div className="settings-form-group">
                                        <label>Date</label>
                                        <input type="date" value={editMeeting.meeting_date} onChange={e => setEditMeeting({ ...editMeeting, meeting_date: e.target.value })} />
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Time</label>
                                        <input type="text" value={editMeeting.meeting_time} onChange={e => setEditMeeting({ ...editMeeting, meeting_time: e.target.value })} />
                                    </div>
                                </div>
                                <div className="settings-form-group">
                                    <label>Venue (Location)</label>
                                    <input type="text" value={editMeeting.venue} onChange={e => setEditMeeting({ ...editMeeting, venue: e.target.value })} placeholder="e.g. Society Clubhouse, Virtual Link, etc." />
                                </div>
                                <div className="settings-form-group">
                                    <label>Notice Room</label>
                                    <select value={editMeeting.notice_room_id || ''} onChange={e => setEditMeeting({ ...editMeeting, notice_room_id: e.target.value })}>
                                        <option value="">Auto-create from eligible members</option>
                                        {noticeRooms.map(room => (
                                            <option key={room.id} value={room.id}>
                                                {room.name}{room.audience_type === 'flats' ? ` (${room.allowed_flat_numbers?.length || 0} flats)` : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="settings-form-group">
                                    <label>Eligible Members ({(editMeeting.eligible_member_ids || []).length} selected)</label>
                                    <div style={{ border: '1px solid #E5E5EA', borderRadius: '10px', padding: '12px', maxHeight: '220px', overflowY: 'auto', display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                                        {members.map(member => (
                                            <label key={member.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#1D1D1F' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={(editMeeting.eligible_member_ids || []).includes(member.id)}
                                                    onChange={() => toggleEditEligibleMember(member.id)}
                                                />
                                                <span>
                                                    <strong>{member.name}</strong> ({member.flat_number || 'No flat'})
                                                    {member.member_type ? ` · ${member.member_type}` : ''}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                                <div className="settings-form-group">
                                    <label>Status</label>
                                    <select value={editMeeting.status} onChange={e => setEditMeeting({ ...editMeeting, status: e.target.value })}>
                                        <option value="SCHEDULED">Scheduled</option>
                                        <option value="COMPLETED">Completed</option>
                                        <option value="CANCELLED">Cancelled</option>
                                    </select>
                                </div>
                                <div className="settings-form-group">
                                    <label>Change Type</label>
                                    <select value={editMeeting.change_action || 'general_update'} onChange={e => setEditMeeting({ ...editMeeting, change_action: e.target.value })}>
                                        <option value="general_update">General Update</option>
                                        <option value="postpone">Postpone</option>
                                        <option value="prepone">Prepone</option>
                                        <option value="cancel">Cancel Meeting</option>
                                    </select>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                                        {[
                                            { key: 'postpone', label: 'Postpone', color: '#D97706' },
                                            { key: 'prepone', label: 'Prepone', color: '#2563EB' },
                                            { key: 'cancel', label: 'Cancel Meeting', color: '#DC2626' },
                                        ].map(action => (
                                            <button
                                                key={action.key}
                                                type="button"
                                                onClick={() => setEditMeeting({ ...editMeeting, change_action: action.key })}
                                                style={{
                                                    padding: '6px 10px',
                                                    borderRadius: '8px',
                                                    border: `1px solid ${action.color}`,
                                                    background: (editMeeting.change_action || 'general_update') === action.key ? action.color : 'white',
                                                    color: (editMeeting.change_action || 'general_update') === action.key ? 'white' : action.color,
                                                    fontSize: '12px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer',
                                                }}
                                            >
                                                {action.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="settings-form-group">
                                    <label>Reason {['cancel', 'postpone', 'prepone'].includes(String(editMeeting.change_action || '')) ? '*' : ''}</label>
                                    <textarea
                                        rows="3"
                                        value={editMeeting.change_reason || ''}
                                        onChange={e => setEditMeeting({ ...editMeeting, change_reason: e.target.value })}
                                        placeholder="Provide reason for cancellation / postpone / prepone"
                                    ></textarea>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '20px' }}>
                                    <div className="settings-form-group">
                                        <label>Eligible Members</label>
                                        <input type="number" value={editMeeting.total_members_eligible} onChange={e => setEditMeeting({ ...editMeeting, total_members_eligible: parseInt(e.target.value) || 0 })} />
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Quorum Required</label>
                                        <input type="number" value={editMeeting.quorum_required} onChange={e => setEditMeeting({ ...editMeeting, quorum_required: parseInt(e.target.value) || 0 })} />
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Quorum Met</label>
                                        <select value={editMeeting.quorum_met ? 'true' : 'false'} onChange={e => setEditMeeting({ ...editMeeting, quorum_met: e.target.value === 'true' })}>
                                            <option value="true">Yes</option>
                                            <option value="false">No</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end', padding: '20px 30px', borderTop: '1px solid #eee', backgroundColor: 'white' }}>
                                <button type="button" onClick={() => setShowEditModal(false)} className="settings-cancel-btn">Cancel</button>
                                <button type="submit" className="settings-save-btn">Save Changes</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Attendance Modal */}
            {showAttendanceModal && selectedMeeting && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '20px', width: '100%', maxWidth: '800px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 40px rgba(0,0,0,0.3)' }}>
                        <div style={{ padding: '30px', borderBottom: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '24px', fontWeight: '800' }}>Mark Attendance</h2>
                            <p style={{ color: '#8E8E93', marginTop: '4px' }}>{selectedMeeting.meeting_title} - {selectedMeeting.meeting_date}</p>
                        </div>
                        <div style={{ flex: 1, overflowY: 'auto', padding: '0 30px' }}>
                            <table className="settings-table" style={{ width: '100%' }}>
                                <thead style={{ position: 'sticky', top: 0, zIndex: 1, backgroundColor: 'white' }}>
                                    <tr>
                                        <th>Member</th>
                                        <th>Flat</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {meetingEligibleMembers.map(member => (
                                        <tr key={member.id}>
                                            <td style={{ fontWeight: '600' }}>{member.name}</td>
                                            <td>{member.flat_number}</td>
                                            <td>
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    {['present', 'absent', 'proxy'].map(status => (
                                                        <button
                                                            key={status}
                                                            type="button"
                                                            onClick={() => setAttendance({ ...attendance, [member.id]: status })}
                                                            style={{
                                                                padding: '6px 12px',
                                                                borderRadius: '6px',
                                                                border: '1px solid #ddd',
                                                                fontSize: '11px',
                                                                fontWeight: '700',
                                                                textTransform: 'uppercase',
                                                                cursor: 'pointer',
                                                                backgroundColor: attendance[member.id] === status ?
                                                                    (status === 'present' ? '#2E8B57' : status === 'proxy' ? '#007AFF' : '#C0392B') : 'white',
                                                                color: attendance[member.id] === status ? 'white' : '#666'
                                                            }}
                                                        >
                                                            {status}
                                                        </button>
                                                    ))}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div style={{ padding: '30px', borderTop: '1px solid #eee', display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>
                            <button onClick={() => setShowAttendanceModal(false)} className="settings-cancel-btn">Cancel</button>
                            <button onClick={handleSaveAttendance} className="settings-save-btn">Save Attendance</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Record Minutes Modal */}
            {showMinutesModal && selectedMeeting && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '20px', width: '100%', maxWidth: '900px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 40px rgba(0,0,0,0.3)' }}>
                        <div style={{ padding: '30px', borderBottom: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '24px', fontWeight: '800' }}>Record Meeting Minutes</h2>
                            <p style={{ color: '#8E8E93', marginTop: '4px' }}>{selectedMeeting.meeting_title}</p>
                        </div>
                        <div style={{ flex: 1, padding: '30px', overflowY: 'auto' }}>
                            <div className="settings-form-group">
                                <label style={{ marginBottom: '10px', display: 'block' }}>Summary of Discussion & Decisions</label>
                                <textarea
                                    style={{ width: '100%', minHeight: '400px', padding: '20px', lineHeight: '1.6', fontSize: '15px' }}
                                    value={minutesText}
                                    onChange={e => setMinutesText(e.target.value)}
                                    placeholder="Enter meeting minutes here..."
                                ></textarea>
                            </div>
                        </div>
                        <div style={{ padding: '30px', borderTop: '1px solid #eee', display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>
                            <button onClick={() => setShowMinutesModal(false)} className="settings-cancel-btn">Cancel</button>
                            <button onClick={handleSaveMinutes} className="settings-save-btn">Save Minutes</button>
                        </div>
                    </div>
                </div>
            )}
            {/* Record Resolution Modal */}
            {showResolutionModal && selectedMeeting && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '20px', width: '100%', maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 10px 40px rgba(0,0,0,0.3)' }}>
                        <div style={{ padding: '30px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h2 style={{ fontSize: '24px', fontWeight: '800' }}>Record Meeting Resolution</h2>
                            <button onClick={() => setShowResolutionModal(false)} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#8E8E93' }}></button>
                        </div>
                        <form onSubmit={handleCreateResolution} style={{ padding: '30px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                <div className="settings-form-group">
                                    <label>Resolution Title *</label>
                                    <input type="text" required value={newResolution.resolution_title} onChange={e => setNewResolution({ ...newResolution, resolution_title: e.target.value })} placeholder="e.g. Approval of Financial Statements" />
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                    <div className="settings-form-group">
                                        <label>Proposed By *</label>
                                        <select required value={newResolution.proposed_by_id} onChange={e => setNewResolution({ ...newResolution, proposed_by_id: e.target.value })}>
                                            <option value="">Select Member</option>
                                            {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.flat_number})</option>)}
                                        </select>
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Seconded By *</label>
                                        <select required value={newResolution.seconded_by_id} onChange={e => setNewResolution({ ...newResolution, seconded_by_id: e.target.value })}>
                                            <option value="">Select Member</option>
                                            {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.flat_number})</option>)}
                                        </select>
                                    </div>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                    <div className="settings-form-group">
                                        <label>Resolution Type</label>
                                        <select value={newResolution.resolution_type} onChange={e => setNewResolution({ ...newResolution, resolution_type: e.target.value })}>
                                            <option value="ordinary">Ordinary Resolution</option>
                                            <option value="special">Special Resolution</option>
                                            <option value="unanimous">Unanimous Resolution</option>
                                        </select>
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Result</label>
                                        <select value={newResolution.result} onChange={e => setNewResolution({ ...newResolution, result: e.target.value })}>
                                            <option value="passed">Passed</option>
                                            <option value="rejected">Rejected</option>
                                            <option value="withdrawn">Withdrawn</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="settings-form-group">
                                    <label>Description / Resolution Text *</label>
                                    <textarea required rows="4" value={newResolution.resolution_text} onChange={e => setNewResolution({ ...newResolution, resolution_text: e.target.value })} placeholder="Enter the full text of the resolution passed..."></textarea>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '12px' }}>
                                    <div className="settings-form-group">
                                        <label>Votes For</label>
                                        <input type="number" value={newResolution.votes_for} onChange={e => setNewResolution({ ...newResolution, votes_for: e.target.value })} />
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Votes Against</label>
                                        <input type="number" value={newResolution.votes_against} onChange={e => setNewResolution({ ...newResolution, votes_against: e.target.value })} />
                                    </div>
                                    <div className="settings-form-group">
                                        <label>Abstentions</label>
                                        <input type="number" value={newResolution.votes_abstain} onChange={e => setNewResolution({ ...newResolution, votes_abstain: e.target.value })} />
                                    </div>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end', marginTop: '30px' }}>
                                <button type="button" onClick={() => setShowResolutionModal(false)} className="settings-cancel-btn">Cancel</button>
                                <button type="submit" className="settings-save-btn">Save Resolution</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MeetingsScreen;

