import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import messagesService from '../services/messagesService';
import { authService } from '../services/authService';
import flatsService from '../services/flatsService';

const MESSAGE_LAST_SEEN_KEY = 'gm_messages_last_seen_at';

const MessagesScreen = () => {
    const navigate = useNavigate();
    const [rooms, setRooms] = useState([]);
    const [selectedRoom, setSelectedRoom] = useState(null);
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [retentionDays, setRetentionDays] = useState(30);
    const [loading, setLoading] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [user, setUser] = useState(null);
    const [flats, setFlats] = useState([]);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newRoomData, setNewRoomData] = useState({
        name: '',
        type: 'general',
        description: '',
        audience_type: 'public',
        allowed_flat_numbers: []
    });
    const messagesEndRef = useRef(null);
    const normalizedRole = String(user?.role || '').toLowerCase();
    const canManageRooms = !['resident', 'member', 'tenant'].includes(normalizedRole);

    useEffect(() => {
        const init = async () => {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
            loadRooms();
            loadFlats();
        };
        init();
    }, []);

    useEffect(() => {
        if (selectedRoom) {
            loadMessages(selectedRoom.id);
        }
    }, [selectedRoom]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const markRoomsSeen = (roomsList) => {
        try {
            const latestRoom = (Array.isArray(roomsList) ? roomsList : [])
                .filter((room) => room.last_message_at)
                .sort((a, b) => new Date(b.last_message_at).getTime() - new Date(a.last_message_at).getTime())[0];
            if (latestRoom?.last_message_at) {
                localStorage.setItem(MESSAGE_LAST_SEEN_KEY, latestRoom.last_message_at);
            }
        } catch (error) {
            // Ignore storage errors
        }
    };

    const loadRooms = async (autoSelectId = null) => {
        setLoading(true);
        try {
            const roomsList = await messagesService.listRooms();
            setRooms(roomsList);
            markRoomsSeen(roomsList);
            if (autoSelectId) {
                const newRoom = roomsList.find(r => r.id === autoSelectId);
                if (newRoom) setSelectedRoom(newRoom);
            } else if (!selectedRoom && roomsList.length > 0) {
                setSelectedRoom(roomsList[0]);
            }
        } catch (error) {
            console.error('Error loading rooms:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadMessages = async (roomId) => {
        setLoadingMessages(true);
        try {
            const messagesList = await messagesService.getMessages(roomId);
            setMessages(messagesList);
        } catch (error) {
            console.error('Error loading messages:', error);
        } finally {
            setLoadingMessages(false);
        }
    };

    const loadFlats = async () => {
        try {
            const data = await flatsService.getFlats();
            const sorted = [...(Array.isArray(data) ? data : [])].sort((a, b) =>
                String(a.flat_number || '').localeCompare(String(b.flat_number || ''), undefined, { numeric: true })
            );
            setFlats(sorted);
        } catch (error) {
            console.error('Error loading flats:', error);
        }
    };

    const toggleRoomFlat = (flatNumber) => {
        const flat = String(flatNumber || '').trim();
        if (!flat) return;
        const selected = newRoomData.allowed_flat_numbers || [];
        setNewRoomData({
            ...newRoomData,
            allowed_flat_numbers: selected.includes(flat)
                ? selected.filter(item => item !== flat)
                : [...selected, flat]
        });
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if ((!newMessage.trim() && !selectedFile) || !selectedRoom) return;

        try {
            const sent = await messagesService.sendMessage(selectedRoom.id, newMessage, {
                file: selectedFile,
                retention_days: retentionDays
            });
            setMessages([...messages, sent]);
            setNewMessage('');
            setSelectedFile(null);
            setRetentionDays(30);
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Failed to send message');
        }
    };

    const downloadAttachment = async (attachment) => {
        try {
            await messagesService.downloadAttachment(attachment.download_url, attachment.file_name);
        } catch (error) {
            console.error('Error downloading attachment:', error);
            alert('Attachment could not be downloaded. It may have expired.');
        }
    };

    const formatExpiry = (value) => {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });
    };

    const handleCreateRoom = async (e) => {
        e.preventDefault();
        if (newRoomData.audience_type === 'flats' && (newRoomData.allowed_flat_numbers || []).length === 0) {
            alert('Select at least one flat for a restricted room.');
            return;
        }
        try {
            const created = await messagesService.createRoom(newRoomData);
            setShowCreateModal(false);
            setNewRoomData({
                name: '',
                type: 'general',
                description: '',
                audience_type: 'public',
                allowed_flat_numbers: []
            });
            loadRooms(created.id);
        } catch (error) {
            console.error('Error creating room:', error);
            alert('Failed to create room. Admin access required.');
        }
    };

    if (loading && rooms.length === 0) {
        return (
            <div className="loading-container">
                <div className="loading-text">Loading chat rooms...</div>
            </div>
        );
    }

    return (
        <div className="dashboard-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="dashboard-header" style={{ flexShrink: 0 }}>
                <div className="dashboard-header-left">
                    <h1 className="dashboard-header-title"> Messages</h1>
                </div>
                <div className="dashboard-header-right">
                    {canManageRooms && (
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="dashboard-logout-button"
                            style={{ marginRight: '12px', backgroundColor: '#fff', color: '#8A3E00' }}
                        >
                            + Add Room
                        </button>
                    )}
                    <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
                         Back to Dashboard
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: '20px', gap: '20px' }}>
                {/* Sidebar - Rooms List */}
                <div style={{
                    width: '320px',
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        padding: '20px',
                        borderBottom: '1px solid #eee',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <span style={{ fontWeight: 'bold', color: '#1D1D1F' }}>Chat Rooms</span>
                        {canManageRooms && (
                            <button
                                onClick={() => setShowCreateModal(true)}
                                style={{
                                    padding: '4px 8px',
                                    borderRadius: '6px',
                                    backgroundColor: '#007AFF',
                                    color: 'white',
                                    border: 'none',
                                    fontSize: '12px',
                                    cursor: 'pointer',
                                    fontWeight: 'bold'
                                }}
                            >
                                + Add Room
                            </button>
                        )}
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto' }}>
                        {rooms.length === 0 ? (
                            <div style={{ padding: '32px 20px', textAlign: 'center', color: '#8E8E93' }}>
                                <div>No chat rooms available.</div>
                                {canManageRooms && (
                                    <button
                                        onClick={() => setShowCreateModal(true)}
                                        style={{
                                            marginTop: '14px',
                                            padding: '8px 12px',
                                            borderRadius: '8px',
                                            backgroundColor: '#007AFF',
                                            color: 'white',
                                            border: 'none',
                                            fontSize: '12px',
                                            cursor: 'pointer',
                                            fontWeight: 'bold'
                                        }}
                                    >
                                        + Add Room
                                    </button>
                                )}
                            </div>
                        ) : (
                            rooms.map(room => (
                                <div
                                    key={room.id}
                                    onClick={() => setSelectedRoom(room)}
                                    style={{
                                        padding: '18px 20px',
                                        cursor: 'pointer',
                                        borderLeft: selectedRoom?.id === room.id ? '4px solid #007AFF' : '4px solid transparent',
                                        backgroundColor: selectedRoom?.id === room.id ? '#F2F2F7' : 'transparent',
                                        transition: '0.2s'
                                    }}
                                >
                                    <div style={{ fontWeight: '700', fontSize: '16px', marginBottom: '5px', color: '#1D1D1F' }}>{room.name}</div>
                                    <div style={{ fontSize: '12px', color: '#8E8E93', textTransform: 'uppercase', letterSpacing: '0' }}>
                                        {room.type}
                                        {room.audience_type === 'flats' ? ` · ${room.allowed_flat_numbers?.length || 0} flats` : ''}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Main Chat Area */}
                <div style={{
                    flex: 1,
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    {selectedRoom ? (
                        <>
                            <div style={{ padding: '22px 24px', borderBottom: '1px solid #eee', background: '#fffaf2' }}>
                                <div style={{ fontWeight: '800', color: '#1D1D1F', fontSize: '22px', marginBottom: selectedRoom.description ? '14px' : '0' }}>{selectedRoom.name}</div>
                                {selectedRoom.description ? (
                                    <div style={{
                                        background: 'linear-gradient(135deg, #FFF3D6 0%, #FFE8DD 100%)',
                                        border: '1px solid #F0C48B',
                                        borderLeft: '6px solid #E8842A',
                                        borderRadius: '8px',
                                        padding: '18px 20px',
                                        boxShadow: '0 8px 20px rgba(138, 62, 0, 0.10)',
                                        color: '#4A2A0A',
                                        fontSize: '17px',
                                        lineHeight: '1.55',
                                        fontWeight: '500'
                                    }}>
                                        <div style={{ fontSize: '12px', color: '#8A3E00', fontWeight: '800', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0' }}>
                                            Announcement
                                        </div>
                                        {selectedRoom.description}
                                        {selectedRoom.audience_type === 'flats' && (
                                            <div style={{ marginTop: '10px', fontSize: '12px', color: '#8E6A3A', fontWeight: '700' }}>
                                                Restricted to {selectedRoom.allowed_flat_numbers?.length || 0} flats
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div style={{ fontSize: '14px', color: '#6b5b4b' }}>
                                        Society message room
                                        {selectedRoom.audience_type === 'flats'
                                            ? ` · Restricted to ${selectedRoom.allowed_flat_numbers?.length || 0} flats`
                                            : ''}
                                    </div>
                                )}
                            </div>

                            <div style={{ flex: 1, overflowY: 'auto', padding: '28px', backgroundColor: '#FFF7EC' }}>
                                {loadingMessages ? (
                                    <div style={{ textAlign: 'center', color: '#8E8E93', marginTop: '20px' }}>Loading messages...</div>
                                ) : messages.length === 0 ? (
                                    <div style={{ textAlign: 'center', color: '#8E8E93', marginTop: '40px', fontSize: '18px' }}>No messages yet. Start the conversation!</div>
                                ) : (
                                    messages.map(msg => (
                                        <div
                                            key={msg.id}
                                            style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                alignItems: 'stretch',
                                                marginBottom: '20px'
                                            }}
                                        >
                                            <div style={{
                                                width: '100%',
                                                padding: '22px 24px',
                                                borderRadius: '8px',
                                                fontSize: '17px',
                                                lineHeight: '1.65',
                                                background: msg.message_type === 'meeting_notice'
                                                    ? 'linear-gradient(135deg, #FFF3D6 0%, #FFE6E0 100%)'
                                                    : 'linear-gradient(135deg, #FFFFFF 0%, #F1F8FF 100%)',
                                                color: '#1D1D1F',
                                                border: '1px solid #F0D7B5',
                                                boxShadow: '0 8px 22px rgba(138, 62, 0, 0.08)'
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start', marginBottom: '10px' }}>
                                                    <div style={{ fontSize: '13px', color: '#8A3E00', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0' }}>
                                                        {msg.sender_name}
                                                    </div>
                                                    <div style={{ fontSize: '12px', color: '#8E8E93', whiteSpace: 'nowrap' }}>
                                                        {new Date(msg.created_at).toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                                    </div>
                                                </div>
                                                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                                                {(msg.attachments || []).length > 0 && (
                                                    <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                                        {msg.attachments.map(file => (
                                                            <button
                                                                key={file.id}
                                                                type="button"
                                                                onClick={() => downloadAttachment(file)}
                                                                style={{
                                                                    border: '1px solid #E8842A',
                                                                    background: '#FFF7EC',
                                                                    color: '#8A3E00',
                                                                    borderRadius: '8px',
                                                                    padding: '10px 12px',
                                                                    cursor: 'pointer',
                                                                    fontWeight: '700',
                                                                    fontSize: '13px'
                                                                }}
                                                            >
                                                                Download {file.file_name}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                                {msg.expires_at && (
                                                    <div style={{ marginTop: '12px', fontSize: '12px', color: '#8E8E93' }}>
                                                        Auto-deletes after {formatExpiry(msg.expires_at)}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            <div style={{ padding: '18px 22px', borderTop: '1px solid #eee', background: '#fff' }}>
                                {selectedFile && (
                                    <div style={{ marginBottom: '10px', color: '#8A3E00', fontSize: '13px', fontWeight: '700' }}>
                                        Attached: {selectedFile.name}
                                    </div>
                                )}
                                <form onSubmit={handleSendMessage} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: '10px', alignItems: 'center' }}>
                                    <input
                                        type="text"
                                        value={newMessage}
                                        onChange={(e) => setNewMessage(e.target.value)}
                                        placeholder={`Message ${selectedRoom.name}...`}
                                        style={{
                                            flex: 1,
                                            padding: '14px 18px',
                                            borderRadius: '24px',
                                            border: '1px solid #E5E5EA',
                                            fontSize: '16px',
                                            outline: 'none'
                                        }}
                                    />
                                    <select
                                        value={retentionDays}
                                        onChange={(e) => setRetentionDays(Number(e.target.value))}
                                        style={{ padding: '12px', borderRadius: '12px', border: '1px solid #E5E5EA', fontSize: '14px' }}
                                    >
                                        <option value={30}>30 days</option>
                                        <option value={60}>60 days</option>
                                        <option value={90}>90 days</option>
                                    </select>
                                    <label style={{
                                        padding: '12px 16px',
                                        borderRadius: '12px',
                                        border: '1px solid #E8842A',
                                        color: '#8A3E00',
                                        fontWeight: '700',
                                        cursor: 'pointer',
                                        whiteSpace: 'nowrap'
                                    }}>
                                        Attach
                                        <input
                                            type="file"
                                            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                                            style={{ display: 'none' }}
                                        />
                                    </label>
                                    <button
                                        type="submit"
                                        style={{
                                            padding: '10px 20px',
                                            borderRadius: '24px',
                                            border: 'none',
                                            backgroundColor: '#007AFF',
                                            color: 'white',
                                            fontWeight: 'bold',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        Send
                                    </button>
                                </form>
                            </div>
                        </>
                    ) : (
                        <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', color: '#8E8E93' }}>
                            Select a chat room to start messaging
                        </div>
                    )}
                </div>
            </div>

            {/* Create Room Modal */}
            {showCreateModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 2000
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '30px',
                        borderRadius: '16px',
                        width: '520px',
                        maxHeight: '90vh',
                        overflowY: 'auto',
                        boxShadow: '0 4px 24px rgba(0,0,0,0.2)'
                    }}>
                        <h2 style={{ marginBottom: '20px', color: '#1D1D1F' }}>Create New Room</h2>
                        <form onSubmit={handleCreateRoom}>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', fontSize: '14px', marginBottom: '5px', color: '#8E8E93' }}>Room Name</label>
                                <input
                                    type="text"
                                    required
                                    value={newRoomData.name}
                                    onChange={(e) => setNewRoomData({ ...newRoomData, name: e.target.value })}
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #E5E5EA', outline: 'none' }}
                                />
                            </div>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', fontSize: '14px', marginBottom: '5px', color: '#8E8E93' }}>Type</label>
                                <select
                                    value={newRoomData.type}
                                    onChange={(e) => setNewRoomData({ ...newRoomData, type: e.target.value })}
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #E5E5EA', outline: 'none' }}
                                >
                                    <option value="general">General</option>
                                    <option value="announcements">Announcements</option>
                                    <option value="maintenance">Maintenance</option>
                                </select>
                            </div>
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ display: 'block', fontSize: '14px', marginBottom: '5px', color: '#8E8E93' }}>Description</label>
                                <textarea
                                    value={newRoomData.description}
                                    onChange={(e) => setNewRoomData({ ...newRoomData, description: e.target.value })}
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #E5E5EA', outline: 'none', height: '80px', resize: 'none' }}
                                />
                            </div>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', fontSize: '14px', marginBottom: '5px', color: '#8E8E93' }}>Audience</label>
                                <select
                                    value={newRoomData.audience_type}
                                    onChange={(e) => setNewRoomData({
                                        ...newRoomData,
                                        audience_type: e.target.value,
                                        allowed_flat_numbers: e.target.value === 'public' ? [] : newRoomData.allowed_flat_numbers
                                    })}
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #E5E5EA', outline: 'none' }}
                                >
                                    <option value="public">All members</option>
                                    <option value="flats">Selected flats only</option>
                                </select>
                            </div>
                            {newRoomData.audience_type === 'flats' && (
                                <div style={{ marginBottom: '20px' }}>
                                    <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', color: '#8E8E93' }}>
                                        Eligible Flats ({newRoomData.allowed_flat_numbers.length} selected)
                                    </label>
                                    <div style={{
                                        maxHeight: '180px',
                                        overflowY: 'auto',
                                        border: '1px solid #E5E5EA',
                                        borderRadius: '8px',
                                        padding: '10px',
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
                                        gap: '8px'
                                    }}>
                                        {flats.length === 0 ? (
                                            <div style={{ color: '#8E8E93', fontSize: '13px', gridColumn: '1 / -1' }}>No flats found. Add flats first.</div>
                                        ) : (
                                            flats.map(flat => {
                                                const flatNumber = String(flat.flat_number || '').trim();
                                                if (!flatNumber) return null;
                                                return (
                                                    <label key={flat.id || flatNumber} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#1D1D1F' }}>
                                                        <input
                                                            type="checkbox"
                                                            checked={newRoomData.allowed_flat_numbers.includes(flatNumber)}
                                                            onChange={() => toggleRoomFlat(flatNumber)}
                                                        />
                                                        {flatNumber}
                                                    </label>
                                                );
                                            })
                                        )}
                                    </div>
                                </div>
                            )}
                            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    style={{ padding: '10px 20px', borderRadius: '8px', border: 'none', backgroundColor: '#F2F2F7', cursor: 'pointer' }}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    style={{ padding: '10px 20px', borderRadius: '8px', border: 'none', backgroundColor: '#007AFF', color: 'white', fontWeight: 'bold', cursor: 'pointer' }}
                                >
                                    Create Room
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MessagesScreen;

