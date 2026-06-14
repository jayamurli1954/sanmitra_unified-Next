import React from 'react';
import { Link } from 'react-router-dom';
import {
  FaBuilding,
  FaCalculator,
  FaCalendarAlt,
  FaChartLine,
  FaCheckCircle,
  FaComments,
  FaEnvelope,
  FaFileInvoice,
  FaGlobe,
  FaPhoneAlt,
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
  {
    name: 'Starter',
    monthly: '₹25 / flat',
    yearly: '₹250 / flat',
    range: 'Minimum 25 flats and up to 50 flats',
    points: ['Core society setup', 'Members and flats', 'Maintenance billing'],
  },
  {
    name: 'Growth',
    monthly: '₹35 / flat',
    yearly: '₹350 / flat',
    range: '51 to 100 flats',
    points: ['Accounting reports', 'Meetings and messages', 'Complaints workflow'],
  },
  {
    name: 'Professional',
    monthly: '₹50 / flat',
    yearly: '₹500 / flat',
    range: '101 flats and above',
    points: ['Advanced billing controls', 'Governance workflows', 'Priority implementation support'],
  },
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
          <Link to="/onboard-society?intent=register" className="landing-nav-link">Register</Link>
          <Link to="/onboard-society?intent=demo" className="landing-nav-link">Request Demo</Link>
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
            <Link to="/onboard-society?intent=register" className="landing-primary-button">Register</Link>
            <Link to="/onboard-society?intent=demo" className="landing-secondary-button">Request Demo</Link>
            <Link to="/login" className="landing-secondary-button">Login</Link>
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
          <h2 id="plans">Clear monthly and yearly pricing for housing societies</h2>
        </div>
        <div className="landing-plan-grid">
          {plans.map((plan) => (
            <article key={plan.name} className="landing-plan-card">
              <h3>{plan.name}</h3>
              <div className="landing-plan-range">{plan.range}</div>
              <div className="landing-plan-rates">
                <div>
                  <span>Monthly</span>
                  <strong>{plan.monthly}</strong>
                </div>
                <div>
                  <span>Yearly</span>
                  <strong>{plan.yearly}</strong>
                </div>
              </div>
              <ul>
                {plan.points.map((point) => <li key={point}>{point}</li>)}
              </ul>
            </article>
          ))}
        </div>
        <div className="landing-implementation-fee">
          One-time implementation, migration, and training fee: <strong>₹5,000</strong>
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <h2>Already managing a society on GruhaMitra?</h2>
          <p>Admins and residents can continue with the existing login and registration flows.</p>
        </div>
        <div className="landing-cta-actions">
          <Link to="/login" className="landing-primary-button">Login</Link>
          <Link to="/onboard-society?intent=demo" className="landing-secondary-button">Request Demo</Link>
        </div>
      </section>

      <section className="landing-contact" aria-labelledby="contact">
        <div className="landing-section-heading">
          <span className="landing-kicker">Contact</span>
          <h2 id="contact">Talk to SanMitra Tech</h2>
        </div>
        <div className="landing-contact-grid">
          <a href="https://wa.me/917904942915" className="landing-contact-card">
            <span><FaPhoneAlt /></span>
            <div>
              <strong>WhatsApp</strong>
              <p>7904942915</p>
            </div>
          </a>
          <a href="mailto:contact@sanmitratech.in" className="landing-contact-card">
            <span><FaEnvelope /></span>
            <div>
              <strong>Email</strong>
              <p>contact@sanmitratech.in</p>
            </div>
          </a>
          <a href="https://www.sanmitratech.in" className="landing-contact-card">
            <span><FaGlobe /></span>
            <div>
              <strong>SanMitra Tech</strong>
              <p>www.sanmitratech.in</p>
            </div>
          </a>
          <a href="https://www.gruhamitra.sanmitratech.in" className="landing-contact-card">
            <span><FaGlobe /></span>
            <div>
              <strong>GruhaMitra</strong>
              <p>www.gruhamitra.sanmitratech.in</p>
            </div>
          </a>
        </div>
      </section>

      <footer className="landing-footer" style={{
        backgroundColor: '#7A3E0C',
        color: 'rgba(255, 255, 255, 0.85)',
        padding: '40px 24px',
        textAlign: 'center',
        borderTop: '2px solid #E8842A',
        marginTop: '60px'
      }}>
        <div style={{
          maxWidth: '1100px',
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '24px',
            flexWrap: 'wrap'
          }}>
            <a href="/gruhamitra/about.html" style={{ color: '#F4A640', textDecoration: 'none', fontWeight: '600', fontSize: '14px' }}>About Us</a>
            <a href="/gruhamitra/contact.html" style={{ color: '#F4A640', textDecoration: 'none', fontWeight: '600', fontSize: '14px' }}>Contact Us</a>
            <a href="/gruhamitra/privacy.html" style={{ color: '#F4A640', textDecoration: 'none', fontWeight: '600', fontSize: '14px' }}>Privacy Policy</a>
            <a href="/gruhamitra/terms.html" style={{ color: '#F4A640', textDecoration: 'none', fontWeight: '600', fontSize: '14px' }}>Terms of Service</a>
          </div>
          <p style={{
            fontSize: '13px',
            color: 'rgba(255, 255, 255, 0.55)',
            margin: 0
          }}>
            © 2026 GruhaMitra. Part of the SanMitra Platform. All rights reserved.
          </p>
        </div>
      </footer>
    </main>
  );
};

export default LandingScreen;
