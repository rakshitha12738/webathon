/* Static demo data to make the UI look populated even without real backend data */

export const STATIC_PATIENTS = [
    {
        id: 'demo-patient-001',
        name: 'Priya Sharma',
        email: 'priya.sharma@example.com',
        latest_risk_status: 'monitor',
        latest_risk_score: 42,
        deviation_flag: true,
        complication_index: 35,
    },
    {
        id: 'demo-patient-002',
        name: 'Rahul Mehta',
        email: 'rahul.mehta@example.com',
        latest_risk_status: 'stable',
        latest_risk_score: 18,
        deviation_flag: false,
        complication_index: 0,
    },
    {
        id: 'demo-patient-003',
        name: 'Ananya Iyer',
        email: 'ananya.iyer@example.com',
        latest_risk_status: 'high_risk',
        latest_risk_score: 81,
        deviation_flag: true,
        complication_index: 35,
    },
    {
        id: 'demo-patient-004',
        name: 'Kiran Patel',
        email: 'kiran.patel@example.com',
        latest_risk_status: 'needs_review',
        latest_risk_score: 63,
        deviation_flag: false,
        complication_index: 0,
    },
    {
        id: 'demo-patient-005',
        name: 'Divya Nair',
        email: 'divya.nair@example.com',
        latest_risk_status: 'stable',
        latest_risk_score: 9,
        deviation_flag: false,
        complication_index: 0,
    },
];

export const STATIC_PATIENT_DETAIL = {
    patient: {
        id: 'demo-patient-001',
        name: 'Priya Sharma',
        email: 'priya.sharma@example.com',
        role: 'patient',
    },
    recovery_profile: {
        condition_type: 'Total Knee Replacement',
        expected_duration_days: 42,
        acceptable_pain_week_1: 5,
        acceptable_pain_week_3: 4,
        start_date: '2026-02-01T00:00:00',
    },
    log_count: 12,
    complication_index: 35,
    latest_risk_score: {
        score: 42,
        status: 'monitor',
        deviation_flag: true,
        complication_index: 35,
    },
    recent_risk_scores: [
        { score: 42, status: 'monitor' },
        { score: 55, status: 'needs_review' },
        { score: 38, status: 'monitor' },
        { score: 29, status: 'stable' },
        { score: 15, status: 'stable' },
    ],
    daily_logs: [
        { date: '2026-02-20', pain_level: 6, mood_level: 3, sleep_hours: 6, appetite: 'fair', swelling: true, body_part: 'Knee', risk_status: 'monitor', note_text: 'Knee swollen in the morning, eased by afternoon.' },
        { date: '2026-02-19', pain_level: 7, mood_level: 2, sleep_hours: 5, appetite: 'poor', swelling: true, body_part: 'Knee', risk_status: 'needs_review', note_text: 'Very restless night, pain was high.' },
        { date: '2026-02-18', pain_level: 5, mood_level: 3, sleep_hours: 7, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Felt better today, did physiotherapy.' },
        { date: '2026-02-17', pain_level: 4, mood_level: 4, sleep_hours: 8, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Good day overall, appetite improving.' },
        { date: '2026-02-16', pain_level: 3, mood_level: 4, sleep_hours: 8, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Walked 200 steps with support.' },
        { date: '2026-02-15', pain_level: 5, mood_level: 3, sleep_hours: 6, appetite: 'fair', swelling: false, body_part: 'Knee', risk_status: 'monitor', note_text: 'Slight stiffness in the evening.' },
    ],
};

export const STATIC_LOGS = [
    { date: '2026-02-20', pain_level: 4, mood_level: 4, sleep_hours: 7.5, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Feeling good. Did physiotherapy exercises.' },
    { date: '2026-02-19', pain_level: 6, mood_level: 3, sleep_hours: 6, appetite: 'fair', swelling: true, body_part: 'Knee', risk_status: 'monitor', note_text: 'Knee was swollen in the morning.' },
    { date: '2026-02-18', pain_level: 3, mood_level: 5, sleep_hours: 8, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Great day! Walked around the garden.' },
    { date: '2026-02-17', pain_level: 5, mood_level: 3, sleep_hours: 7, appetite: 'good', swelling: false, body_part: 'Knee', risk_status: 'stable', note_text: 'Some stiffness but manageable.' },
    { date: '2026-02-16', pain_level: 7, mood_level: 2, sleep_hours: 5, appetite: 'poor', swelling: true, body_part: 'Knee', risk_status: 'needs_review', note_text: 'Bad night. Pain woke me up twice.' },
];

export const STATIC_GUIDANCE = {
    stage: 'Week 3',
    days_since_start: 19,
    focus: 'Gradual activity increase',
    acceptable_pain_range: '0-4',
    current_risk_status: 'stable',
    risk_score: 22,
    recommendations: [
        'Begin gentle exercises as recommended by your physiotherapist',
        'Gradually increase activity level — short walks encouraged',
        'Continue medication as directed; do not skip doses',
        'Monitor pain levels carefully and log daily',
        'Attend physical therapy sessions as prescribed',
    ],
    warning_signs: [
        'Increasing or worsening pain trend over 3+ days',
        'Pain levels exceeding the acceptable range (4+)',
        'Swelling that worsens or does not reduce with ice',
        'Signs of infection (redness, heat, discharge)',
        'Limited or worsening mobility',
    ],
};
