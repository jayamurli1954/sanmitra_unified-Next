import React from 'react';
import { Link } from 'react-router-dom';
import {
  FaBuilding,
  FaCalculator,
  FaCalendarAlt,
  FaChartLine,
  FaCheckCircle,
  FaComments,
  FaFileInvoice,
  FaTools,
  FaUsers,
} from 'react-icons/fa';

const publicAsset = (path) => `/gruhamitra/${path}`;

const featureCards = [
  {
    icon: <FaFileInvoice />,
    title: 'Maintenance Billing',
    text: 'Generate monthly bills from society rules, fixed expenses, water usage, funds, and flat-level charges.',
  },
  {
    icon: <FaCalculator />,
    title: 'MitraBooks Accounting',
    text: 'Collections, expenses, vouchers, ledgers, trial balance, and reports remain tied to shared accounting.',
  },
  {
    icon: <FaUsers />,
    title: 'Members And Flats',
    text: 'Maintain blocks, flats, owners, tenants, occupants, join requests, and member lifecycle details.',
  },
  {
    icon: <FaTools />,
    title: 'Complaints',
    text: 'Track complaints, service requests, statuses, assignments, and closure activity in one place.',
  },
  {
    icon: <FaCalendarAlt />,
    title: 'Meetings',
    text: 'Schedule committee or society meetings, send notices, track attendance, minutes, and resolutions.',
  },
  {
    icon: <FaComments />,
    title: 'Messages',
    text: 'Keep residents informed through notice-room messaging and society-level communication.',
  },
];

const plans = [
  { name: 'Starter', price: 'Rs. 1,000 + Rs. 25 / flat', points: ['Core society setup', 'Members and flats', 'Maintenance billing'] },
  { name: 'Growth', price: 'Rs. 1,500 + Rs. 40 / flat', points: ['Accounting reports', 'Meetings and messages', 'Complaints workflow'] },
  { name: 'Professional', price: 'Rs. 2,500 + Rs. 50 / flat', points: ['Advanced billing controls', 'Governance workflows', 'Priority implementation support'] },
];

const LandingScreen = () => {
  return (
    <main className="landing-page">
      <header className="landing-nav">
        <Link to="/" className="landing-brand" aria-label="GruhaMitra home">
          <img src={publicAsset('GruhaMitra_Logo.png')} alt="GruhaMitra logo" />
          <span>GruhaMitra</span>
        </Link>
        <nav className="landing-nav-actions" aria-label="GruhaMitra entry actions">
          <Link to="/resident-signup" className="landing-nav-link">Join Society</Link>
          <Link to="/onboard-society" className="landing-nav-link">Register Society</Link>
          <Link to="/login" className="landing-nav-button">Login</Link>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="landing-kicker">Housing society operations with MitraBooks accounting</div>
          <h1>Run your RWA or apartment society with clearer billing, collections, and communication.</h1>
          <p>
            GruhaMitra brings flats, members, maintenance billing, complaints, meetings, messages,
            and society accounting into one practical workspace for committees and residents.
          </p>
          <div className="landing-hero-actions">
            <Link to="/onboard-society" className="landing-primary-button">Register Society</Link>
            <Link to="/login" className="landing-secondary-button">Existing User Login</Link>
          </div>
          <div className="landing-trust-row">
            <span><FaCheckCircle /> Tenant-scoped society data</span>
            <span><FaCheckCircle /> Shared MitraBooks accounting</span>
            <span><FaCheckCircle /> Admin and resident workflows</span>
          </div>
        </div>
        <div className="landing-hero-visual" aria-label="GruhaMitra application preview">
          <div className="landing-product-panel">
            <div className="landing-product-topline">
              <img src={publicAsset('GruhaMitra_Logo.png')} alt="GruhaMitra logo" />
              <div>
                <strong>GruhaMitra Society</strong>
                <span>Admin Command Center</span>
              </div>
            </div>
            <div className="landing-product-metrics">
              <div><span>Billing</span><strong>Rs. 50,756</strong></div>
              <div><span>Dues</span><strong>Rs. 45,341</strong></div>
              <div><span>Members</span><strong>52</strong></div>
            </div>
            <div className="landing-product-flow">
              <span>Expenses</span>
              <span>Bill Rules</span>
              <span>Member Dues</span>
              <span>Accounting</span>
            </div>
            <div className="landing-product-activity">
              <p><strong>Meeting notice posted</strong><span>Visible to eligible members</span></p>
              <p><strong>Maintenance receipt posted</strong><span>Updated member dues and ledger</span></p>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-preview-band" aria-labelledby="product-views">
        <div className="landing-section-heading">
          <span className="landing-kicker">Application Views</span>
          <h2 id="product-views">A working interface for society admins and residents</h2>
        </div>
        <div className="landing-preview-grid">
          <figure>
            <img src={publicAsset('landing/gruhamitra_admin_preview.png')} alt="GruhaMitra admin dashboard preview" />
            <figcaption>Admin dashboard for billing, dues, complaints, and accounting visibility.</figcaption>
          </figure>
          <figure>
            <img src={publicAsset('landing/gruhamitra_resident_preview.png')} alt="GruhaMitra resident portal preview" />
            <figcaption>Resident portal for society activity, payments, notices, and service requests.</figcaption>
          </figure>
        </div>
      </section>

      <section className="landing-flow-section" aria-labelledby="operating-flow">
        <div className="landing-section-heading">
          <span className="landing-kicker">Operating Flow</span>
          <h2 id="operating-flow">From monthly expenses to member dues</h2>
        </div>
        <div className="landing-flow">
          <div><FaBuilding /><span>Society setup</span></div>
          <div><FaUsers /><span>Flats and members</span></div>
          <div><FaFileInvoice /><span>Generate bills</span></div>
          <div><FaCalculator /><span>Post accounting</span></div>
          <div><FaChartLine /><span>Reports and dues</span></div>
        </div>
      </section>

      <section className="landing-features" aria-labelledby="features">
        <div className="landing-section-heading">
          <span className="landing-kicker">Features</span>
          <h2 id="features">The daily workflows an RWA needs</h2>
        </div>
        <div className="landing-feature-grid">
          {featureCards.map((feature) => (
            <article key={feature.title} className="landing-feature-card">
              <span className="landing-feature-icon">{feature.icon}</span>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-plans" aria-labelledby="plans">
        <div className="landing-section-heading">
          <span className="landing-kicker">Plans</span>
          <h2 id="plans">Simple monthly pricing for housing societies</h2>
        </div>
        <div className="landing-plan-grid">
          {plans.map((plan) => (
            <article key={plan.name} className="landing-plan-card">
              <h3>{plan.name}</h3>
              <div className="landing-plan-price">{plan.price}</div>
              <ul>
                {plan.points.map((point) => <li key={point}>{point}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <h2>Already managing a society on GruhaMitra?</h2>
          <p>Admins and residents can continue with the existing login and registration flows.</p>
        </div>
        <div className="landing-cta-actions">
          <Link to="/login" className="landing-primary-button">Login</Link>
          <Link to="/resident-signup" className="landing-secondary-button">Join Existing Society</Link>
        </div>
      </section>
    </main>
  );
};

export default LandingScreen;
