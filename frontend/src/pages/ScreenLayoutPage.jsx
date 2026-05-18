import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { screensAPI } from '../api';

export default function ScreenLayoutPage() {
  const { screenId } = useParams();
  const navigate = useNavigate();

  const { data: screensData } = useQuery({ queryKey: ['screens'], queryFn: () => screensAPI.list().then(r => r.data) });
  const screens = screensData?.results || screensData || [];
  const screen = screens.find(s => s.id === parseInt(screenId));

  const { data: showsData, isLoading: isLoadingShows } = useQuery({
    queryKey: ['shows', screenId],
    queryFn: () => screensAPI.shows({ screen: screenId }).then(r => r.data),
    enabled: !!screenId
  });

  const shows = showsData?.results || showsData || [];
  const [selectedShowId, setSelectedShowId] = useState('');

  const { data: seatMapData, isLoading: isLoadingSeatMap } = useQuery({
    queryKey: ['seatMap', selectedShowId],
    queryFn: () => screensAPI.showSeatMap(selectedShowId).then(r => r.data),
    enabled: !!selectedShowId
  });

  if (!screen) return <div style={{ padding: '24px' }}>Loading screen...</div>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/builder')} style={{ marginBottom: '12px' }}>← Back to Builder</button>
          <h1 className="page-title">🗺️ Layout & Occupancy: {screen.name}</h1>
          <p className="page-subtitle">View seat status across all categories for specific shows.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ marginBottom: '16px' }}>
          <label className="form-label">Select a Show to view live layout</label>
          {isLoadingShows ? (
            <div className="text-muted">Loading shows...</div>
          ) : (
            <select 
              className="form-input" 
              value={selectedShowId} 
              onChange={e => setSelectedShowId(e.target.value)}
              style={{ maxWidth: '400px' }}
            >
              <option value="">-- Choose a Show --</option>
              {shows.map(s => (
                <option key={s.id} value={s.id}>
                  {s.show_date} | {s.start_time} - {s.movie_title}
                </option>
              ))}
            </select>
          )}
          {shows.length === 0 && !isLoadingShows && (
            <div className="text-warning text-sm" style={{ marginTop: '8px' }}>No shows scheduled for this screen yet.</div>
          )}
        </div>
      </div>

      {selectedShowId && (
        <div className="card">
          {isLoadingSeatMap ? (
            <div className="text-center text-muted" style={{ padding: '40px' }}>Loading Seat Map...</div>
          ) : seatMapData ? (
            <div>
              <div className="grid-4" style={{ marginBottom: '24px' }}>
                <div className="stat-card">
                  <div className="stat-title">Total Capacity</div>
                  <div className="stat-value">{seatMapData.stats.total_seats}</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--success)' }}>
                  <div className="stat-title">Online Bookings</div>
                  <div className="stat-value">{seatMapData.stats.online_bookings}</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--warning)' }}>
                  <div className="stat-title">Offline (Counter)</div>
                  <div className="stat-value">{seatMapData.stats.offline_bookings}</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--primary)' }}>
                  <div className="stat-title">Total Booked</div>
                  <div className="stat-value">{seatMapData.stats.total_bookings}</div>
                </div>
              </div>

              <div className="flex gap-16" style={{ marginBottom: '32px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <div className="flex gap-4" style={{ alignItems: 'center' }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: '4px', border: '2px solid var(--border)', background: 'transparent' }} />
                  <span className="text-sm">Available</span>
                </div>
                <div className="flex gap-4" style={{ alignItems: 'center' }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: '4px', background: 'var(--success)' }} />
                  <span className="text-sm">Online Booking</span>
                </div>
                <div className="flex gap-4" style={{ alignItems: 'center' }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: '4px', background: 'var(--warning)' }} />
                  <span className="text-sm">Offline Booking</span>
                </div>
              </div>

              <div style={{ background: '#111118', padding: '40px 20px', borderRadius: '12px', overflowX: 'auto' }}>
                <div style={{ 
                  background: 'linear-gradient(to bottom, rgba(255,255,255,0.1), transparent)', 
                  height: '40px', 
                  borderRadius: '100% 100% 0 0', 
                  margin: '0 auto 60px auto', 
                  maxWidth: '600px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'rgba(255,255,255,0.3)',
                  letterSpacing: '10px',
                  textTransform: 'uppercase',
                  fontSize: '12px',
                  borderTop: '2px solid rgba(255,255,255,0.2)'
                }}>
                  SCREEN
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
                  {Object.entries(
                    seatMapData.seats.reduce((acc, seat) => {
                      if (!acc[seat.row]) acc[seat.row] = [];
                      acc[seat.row].push(seat);
                      return acc;
                    }, {})
                  )
                  .sort(([rowA], [rowB]) => rowA.localeCompare(rowB))
                  .map(([row, seatsInRow]) => (
                    <div key={row} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <div style={{ width: '24px', fontWeight: 'bold', color: 'var(--text-muted)' }}>{row}</div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        {seatsInRow.sort((a, b) => a.number - b.number).map(seat => {
                          let bgColor = 'transparent';
                          let borderColor = seat.color;
                          let textColor = '#FFFFFF';
                          let opacity = 1;

                          if (seat.state === 'BOOKED') {
                            if (seat.source === 'APP' || seat.source === 'BMS') {
                              bgColor = 'var(--success)';
                              borderColor = 'var(--success)';
                            } else {
                              bgColor = 'var(--warning)';
                              borderColor = 'var(--warning)';
                            }
                          } else if (seat.state !== 'AVAILABLE') {
                            bgColor = 'var(--border)';
                            borderColor = 'var(--border)';
                            opacity = 0.5;
                          }

                          return (
                            <div 
                              key={seat.id} 
                              title={`Row ${seat.row} - Seat ${seat.number} (${seat.category})`}
                              style={{
                                width: '30px', 
                                height: '30px', 
                                borderRadius: '4px 4px 8px 8px',
                                border: `2px solid ${borderColor}`,
                                backgroundColor: bgColor,
                                color: textColor,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '10px',
                                fontWeight: '600',
                                opacity: opacity,
                                cursor: 'default'
                              }}
                            >
                              {seat.number}
                            </div>
                          );
                        })}
                      </div>
                      <div style={{ width: '24px', fontWeight: 'bold', color: 'var(--text-muted)', textAlign: 'right' }}>{row}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
