/**
 * AI Receptionist Dashboard - Main Application
 * 
 * Features:
 * - Real-time slot state visualization
 * - Countdown timer for active locks
 * - Appointment conversion funnel
 * - Manual override controls
 */

import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [businessId, setBusinessId] = useState('test_business');
  const [dashboardData, setDashboardData] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update current time every second for countdown timers
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/status`, {
        params: { business_id: businessId }
      });
      setDashboardData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch dashboard data: ' + err.message);
    }
  };

  // Fetch appointments
  const fetchAppointments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/appointments/list`, {
        params: { business_id: businessId, status: 'CONFIRMED' }
      });
      setAppointments(response.data.appointments);
      setError(null);
    } catch (err) {
      setError('Failed to fetch appointments: ' + err.message);
    }
  };

  // Initial load and refresh every 5 seconds
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboardData(), fetchAppointments()]);
      setLoading(false);
    };

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [businessId]);

  // Cancel appointment
  const handleCancelAppointment = async (appointmentId, customerPhone) => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) {
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/appointments/cancel`, {
        appointment_id: appointmentId,
        customer_phone: customerPhone
      });

      if (response.data.success) {
        alert('Appointment cancelled successfully');
        fetchAppointments();
        fetchDashboardData();
      } else {
        alert('Failed to cancel: ' + response.data.reason);
      }
    } catch (err) {
      alert('Error cancelling appointment: ' + err.message);
    }
  };

  // Calculate time remaining for lock
  const calculateTimeRemaining = (expiresAt) => {
    const expiry = new Date(expiresAt);
    const diff = expiry - currentTime;
    if (diff <= 0) return 'Expired';
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'AVAILABLE':
        return 'green';
      case 'LOCKED':
        return 'yellow';
      case 'BOOKED':
        return 'blue';
      default:
        return 'gray';
    }
  };

  if (loading) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>AI Receptionist Dashboard</h1>
          <p>Loading...</p>
        </header>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>🤖 AI Receptionist Dashboard</h1>
        <p className="subtitle">Production-Grade Appointment Booking System</p>
      </header>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {dashboardData && (
        <div className="dashboard-container">
          {/* Key Metrics */}
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>Active Locks</h3>
              <div className="metric-value">{dashboardData.active_locks_count}</div>
              <p className="metric-label">Currently in conversation</p>
            </div>

            <div className="metric-card">
              <h3>Today's Appointments</h3>
              <div className="metric-value">{dashboardData.today_appointments_count}</div>
              <p className="metric-label">Confirmed bookings</p>
            </div>

            <div className="metric-card">
              <h3>Total Confirmed</h3>
              <div className="metric-value">{dashboardData.confirmed_appointments_count}</div>
              <p className="metric-label">All time</p>
            </div>

            <div className="metric-card">
              <h3>Conversion Rate</h3>
              <div className="metric-value">{dashboardData.conversion_rate.toFixed(1)}%</div>
              <p className="metric-label">Lock → Booking</p>
            </div>
          </div>

          {/* Recent Slots Activity */}
          <div className="section">
            <h2>Real-Time Slot Status</h2>
            <div className="slots-container">
              {dashboardData.recent_slots.length === 0 ? (
                <p className="no-data">No recent activity</p>
              ) : (
                dashboardData.recent_slots.map((slot, index) => (
                  <div key={index} className={`slot-card status-${slot.status.toLowerCase()}`}>
                    <div className="slot-header">
                      <span className={`status-badge ${getStatusColor(slot.status)}`}>
                        {slot.status}
                      </span>
                      <span className="slot-time">
                        {new Date(slot.start_datetime).toLocaleString()}
                      </span>
                    </div>
                    
                    <div className="slot-details">
                      {slot.status === 'LOCKED' && (
                        <>
                          <p><strong>Customer:</strong> {slot.customer_phone}</p>
                          <p className="countdown">
                            <strong>Expires in:</strong> 
                            <span className="timer">{calculateTimeRemaining(slot.lock_expires_at)}</span>
                          </p>
                        </>
                      )}
                      
                      {slot.status === 'BOOKED' && (
                        <>
                          <p><strong>Customer:</strong> {slot.customer_phone}</p>
                          <p><strong>Appointment ID:</strong> {slot.appointment_id}</p>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Appointments List */}
          <div className="section">
            <h2>Confirmed Appointments</h2>
            <div className="appointments-table">
              {appointments.length === 0 ? (
                <p className="no-data">No confirmed appointments</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Customer</th>
                      <th>Phone</th>
                      <th>Service</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.map((apt) => (
                      <tr key={apt.appointment_id}>
                        <td>{new Date(apt.start_datetime).toLocaleString()}</td>
                        <td>{apt.customer_name}</td>
                        <td>{apt.customer_phone}</td>
                        <td>{apt.service_type}</td>
                        <td>
                          <span className={`status-badge ${getStatusColor('BOOKED')}`}>
                            {apt.status}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-cancel"
                            onClick={() => handleCancelAppointment(apt.appointment_id, apt.customer_phone)}
                          >
                            Cancel
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* System Information */}
          <div className="section">
            <h2>System Information</h2>
            <div className="info-grid">
              <div className="info-item">
                <strong>Business ID:</strong> {dashboardData.business_id}
              </div>
              <div className="info-item">
                <strong>Last Updated:</strong> {formatDistanceToNow(currentTime, { addSuffix: true })}
              </div>
              <div className="info-item">
                <strong>Auto-refresh:</strong> Every 5 seconds
              </div>
            </div>
          </div>
        </div>
      )}

      <footer className="App-footer">
        <p>AI Receptionist Appointment Booking System v1.0.0</p>
        <p className="footer-note">
          Deterministic • Production-Grade • Double-Booking Impossible
        </p>
      </footer>
    </div>
  );
}

export default App;
