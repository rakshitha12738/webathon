import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import PatientDashboard from './pages/PatientDashboard'
import DoctorDashboard from './pages/DoctorDashboard'

function PrivateRoute({ children, role }) {
    const token = localStorage.getItem('token');
    const userRole = localStorage.getItem('role');

    if (!token) return <Navigate to="/login" />;
    if (role && userRole !== role) return <Navigate to={userRole === 'doctor' ? '/doctor' : '/patient'} />;

    return children;
}

export default function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                <Route path="/patient/*" element={
                    <PrivateRoute role="patient">
                        <PatientDashboard />
                    </PrivateRoute>
                } />

                <Route path="/doctor/*" element={
                    <PrivateRoute role="doctor">
                        <DoctorDashboard />
                    </PrivateRoute>
                } />

                <Route path="/" element={<Navigate to="/login" />} />
            </Routes>
        </Router>
    )
}
