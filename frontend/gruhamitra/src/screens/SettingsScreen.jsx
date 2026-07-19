/**
 * GruhaMitra Settings Screen
 * Master control panel with 14 sub-modules
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SocietyProfileTab from './settings/SocietyProfileTab';
import FlatsBlocksTab from './settings/FlatsBlocksTab';
import MemberConfigTab from './settings/MemberConfigTab';
import BillingRulesTab from './settings/BillingRulesTab';
import LateFeeTab from './settings/LateFeeTab';
import AccountingTab from './settings/AccountingTab';
import PaymentGatewayTab from './settings/PaymentGatewayTab';
import NotificationsTab from './settings/NotificationsTab';
import RolesTab from './settings/RolesTab';
import ComplaintsTab from './settings/ComplaintsTab';
import AssetsTab from './settings/AssetsTab';
import LegalTab from './settings/LegalTab';
import DataSecurityTab from './settings/DataSecurityTab';
import MultiSocietyTab from './settings/MultiSocietyTab';
import VisitorBrandsTab from './settings/VisitorBrandsTab';
import StaffRegistryTab from './settings/StaffRegistryTab';

const SettingsScreen = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('society-profile');

  const settingsTabs = [
    { id: 'society-profile', label: 'Society Profile', icon: 'SP' },
    { id: 'flats-blocks', label: 'Flats & Blocks', icon: 'FB' },
    { id: 'member-config', label: 'Member Configuration', icon: 'MC' },
    { id: 'billing-rules', label: 'Billing Rules', icon: 'BR' },
    { id: 'late-fee', label: 'Late Fee & Penalties', icon: 'LF' },
    { id: 'accounting', label: 'Accounting Settings', icon: 'AC' },
    { id: 'payment-gateway', label: 'Payment Gateway', icon: 'PG' },
    { id: 'notifications', label: 'Notifications', icon: 'NT' },
    { id: 'roles', label: 'Roles & Permissions', icon: 'RP' },
    { id: 'complaints', label: 'Complaints & Helpdesk', icon: 'CH' },
    { id: 'assets', label: 'Assets & Vendors', icon: 'AV' },
    { id: 'legal', label: 'Legal & Compliance', icon: 'LC' },
    { id: 'data-security', label: 'Data & Security', icon: 'DS' },
    { id: 'multi-society', label: 'Multi-Society Mode', icon: 'MS' },
    { id: 'visitor-brands', label: 'Visitor Brands', icon: 'VB' },
    { id: 'staff-registry', label: 'Staff Registry', icon: 'SR' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'society-profile':
        return <SocietyProfileTab />;
      case 'flats-blocks':
        return <FlatsBlocksTab />;
      case 'member-config':
        return <MemberConfigTab />;
      case 'billing-rules':
        return <BillingRulesTab />;
      case 'late-fee':
        return <LateFeeTab />;
      case 'accounting':
        return <AccountingTab />;
      case 'payment-gateway':
        return <PaymentGatewayTab />;
      case 'notifications':
        return <NotificationsTab />;
      case 'roles':
        return <RolesTab />;
      case 'complaints':
        return <ComplaintsTab />;
      case 'assets':
        return <AssetsTab />;
      case 'legal':
        return <LegalTab />;
      case 'data-security':
        return <DataSecurityTab />;
      case 'multi-society':
        return <MultiSocietyTab />;
      case 'visitor-brands':
        return <VisitorBrandsTab />;
      case 'staff-registry':
        return <StaffRegistryTab />;
      default:
        return <SocietyProfileTab />;
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title">Settings</h1>
          <span className="dashboard-header-subtitle">Master Control Panel</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
            Back to Dashboard
          </button>
        </div>
      </div>

      <div className="settings-container">
        {/* Sidebar Navigation */}
        <div className="settings-sidebar">
          <div className="settings-sidebar-header">
            <h3>Settings Menu</h3>
          </div>
          <nav className="settings-nav">
            {settingsTabs.map((tab) => (
              <button
                key={tab.id}
                className={`settings-nav-item ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="settings-nav-icon">{tab.icon}</span>
                <span className="settings-nav-label">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content Area */}
        <div className="settings-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default SettingsScreen;
