import { useState, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { screensAPI } from '../api';
import toast from 'react-hot-toast';
import { format, addDays } from 'date-fns';

export default function ShowsPage() {
  const qc = useQueryClient();
  const dateScrollRef = useRef(null);
  const [showForm, setShowForm] = useState(false);
  const [movieForm, setMovieForm] = useState(false);
  const [form, setForm] = useState({ screen: '', movie: '', show_date: '', start_time: '', end_time: '', duration_hours: 2.5, base_price: 0 });
  const [mForm, setMForm] = useState({ title: '', language: 'Tamil', genre: '', duration_minutes: 150, certificate: 'U/A', description: '' });
  
  const today = new Date();
  const dateTabs = Array.from({ length: 7 }).map((_, i) => {
    const d = addDays(today, i);
    return { dateObj: d, dateStr: format(d, 'yyyy-MM-dd'), day: format(d, 'EEE').toUpperCase(), dayNum: format(d, 'dd'), month: format(d, 'MMM').toUpperCase() };
  });
  
  const [selectedDate, setSelectedDate] = useState(dateTabs[0].dateStr);
  const [startIndex, setStartIndex] = useState(0);
  const visibleCount = 3;
  const visibleDates = dateTabs.slice(startIndex, startIndex + visibleCount);

  const handlePrevDate = () => {
    if (startIndex > 0) setStartIndex(s => s - 1);
  };
  const handleNextDate = () => {
    if (startIndex + visibleCount < dateTabs.length) setStartIndex(s => s + 1);
  };

  const { data: shows, isLoading } = useQuery({ queryKey: ['shows'], queryFn: () => screensAPI.shows().then(r => r.data) });
  const { data: movies } = useQuery({ queryKey: ['movies'], queryFn: () => screensAPI.movies().then(r => r.data) });
  const { data: screens } = useQuery({ queryKey: ['screens'], queryFn: () => screensAPI.list().then(r => r.data) });
  
  const showMut = useMutation({
    mutationFn: d => screensAPI.createShow(d),
    onSuccess: () => { qc.invalidateQueries(['shows']); toast.success('Show scheduled!'); setShowForm(false); },
    onError: e => toast.error(e.response?.data?.detail || 'Failed'),
  });
  const movieMut = useMutation({
    mutationFn: d => screensAPI.createMovie(d),
    onSuccess: () => { qc.invalidateQueries(['movies']); toast.success('Movie added!'); setMovieForm(false); },
    onError: () => toast.error('Failed to add movie'),
  });
  const deleteMovieMut = useMutation({
    mutationFn: id => screensAPI.deleteMovie(id),
    onSuccess: () => { qc.invalidateQueries(['movies']); qc.invalidateQueries(['shows']); toast.success('Movie deleted!'); },
    onError: () => toast.error('Cannot delete movie. It may have existing bookings.'),
  });
  const deleteShowMut = useMutation({
    mutationFn: id => screensAPI.deleteShow(id),
    onSuccess: () => { qc.invalidateQueries(['shows']); toast.success('Show deleted!'); },
    onError: () => toast.error('Cannot delete show. It may have existing bookings.'),
  });
  
  const records = shows?.results || shows || [];
  const movieList = movies?.results || movies || [];
  const screenList = Array.isArray(screens) ? screens : (screens?.results || []);

  const groupedShows = useMemo(() => {
    const filtered = records.filter(r => r.show_date === selectedDate);
    const groups = {};
    filtered.forEach(s => {
      if (!groups[s.movie]) {
        // Find full movie details from catalog
        const m = movieList.find(x => x.id === s.movie) || {};
        groups[s.movie] = {
          id: s.movie,
          title: s.movie_title,
          language: s.movie_language,
          certificate: s.movie_certificate,
          genre: m.genre || 'Unknown',
          duration: s.movie_duration || m.duration_minutes || 0,
          screens: {}
        };
      }
      if (!groups[s.movie].screens[s.screen_name]) {
        groups[s.movie].screens[s.screen_name] = [];
      }
      groups[s.movie].screens[s.screen_name].push(s);
    });
    return Object.values(groups);
  }, [records, selectedDate, movieList]);



  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div><h1 className="page-title">🎬 Movies</h1><p className="page-subtitle">Manage Movies & Show Timings</p></div>
        <div className="flex gap-12">
          <button className="btn btn-secondary" onClick={() => setMovieForm(true)}>+ Add Movie</button>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Schedule Show</button>
        </div>
      </div>
      
      {/* Date Selector Tabs with Arrows */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
        <div className="card" style={{ padding: 0, display: 'flex', alignItems: 'center', backgroundColor: 'var(--bg-glass)', width: 'fit-content' }}>
          <button 
            onClick={handlePrevDate} 
            disabled={startIndex === 0}
            style={{ padding: '12px', background: 'transparent', border: 'none', color: startIndex === 0 ? 'var(--border)' : 'var(--text-muted)', cursor: startIndex === 0 ? 'not-allowed' : 'pointer', fontSize: '18px' }}>
            &#10094;
          </button>
          
          <div style={{ display: 'flex', overflow: 'hidden', justifyContent: 'center' }}>
            {visibleDates.map(tab => {
              const isActive = tab.dateStr === selectedDate;
              return (
                <div 
                  key={tab.dateStr} 
                  onClick={() => setSelectedDate(tab.dateStr)}
                  style={{
                    padding: '8px 16px',
                    minWidth: '60px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    backgroundColor: isActive ? 'var(--primary)' : 'transparent',
                    color: isActive ? '#fff' : 'var(--text-muted)',
                    borderRight: '1px solid var(--border)',
                    borderLeft: '1px solid var(--border)',
                    transition: 'all 0.2s',
                    flexShrink: 0
                  }}
                >
                  <div style={{ fontSize: '10px', fontWeight: 600 }}>{tab.day}</div>
                  <div style={{ fontSize: '16px', fontWeight: 700, margin: '2px 0' }}>{tab.dayNum}</div>
                  <div style={{ fontSize: '9px' }}>{tab.month}</div>
                </div>
              );
            })}
          </div>
          
          <button 
            onClick={handleNextDate} 
            disabled={startIndex + visibleCount >= dateTabs.length}
            style={{ padding: '12px', background: 'transparent', border: 'none', color: startIndex + visibleCount >= dateTabs.length ? 'var(--border)' : 'var(--text-muted)', cursor: startIndex + visibleCount >= dateTabs.length ? 'not-allowed' : 'pointer', fontSize: '18px' }}>
            &#10095;
          </button>
        </div>
      </div>

      {/* Movies & Shows List */}
      <div className="card" style={{ padding: 0 }}>
        {isLoading && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading shows...</div>}
        {!isLoading && groupedShows.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No shows scheduled for this date.</div>
        )}
        
        {groupedShows.map((movie, idx) => (
          <div key={movie.id} style={{ 
            display: 'flex', 
            padding: '24px', 
            borderBottom: idx < groupedShows.length - 1 ? '1px solid var(--border)' : 'none',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <div style={{ width: '300px', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>{movie.title}</h3>
                  <button 
                    onClick={() => { if(window.confirm('Are you sure you want to completely remove this movie?')) deleteMovieMut.mutate(movie.id); }}
                    style={{ background: 'transparent', border: 'none', color: 'var(--error)', cursor: 'pointer', padding: '4px', opacity: 0.7 }}
                    title="Remove Movie"
                  >
                    🗑️
                  </button>
                </div>
                
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {movie.certificate && <span style={{ fontSize: '10px', padding: '2px 6px', border: '1px solid var(--text-muted)', borderRadius: '4px', color: 'var(--text-muted)' }}>{movie.certificate}</span>}
                  <span style={{ fontSize: '10px', padding: '2px 6px', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text)' }}>{movie.language}</span>
                  <span style={{ fontSize: '10px', padding: '2px 6px', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text)' }}>{movie.genre}</span>
                  <span style={{ fontSize: '10px', padding: '2px 6px', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text)' }}>{movie.duration} mins</span>
                </div>
              </div>
              
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {Object.entries(movie.screens).map(([screenName, shows]) => (
                  <div key={screenName} style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <div style={{ width: '100px', fontSize: '14px', fontWeight: 500, color: 'var(--text-muted)', paddingTop: '8px' }}>
                      {screenName}
                    </div>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', flex: 1 }}>
                      {shows.sort((a,b) => a.start_time.localeCompare(b.start_time)).map(show => {
                        const [h, m] = show.start_time.split(':');
                        const dateObj = new Date();
                        dateObj.setHours(parseInt(h), parseInt(m));
                        const timeStr = format(dateObj, 'hh:mm a');
                        
                        return (
                          <div key={show.id} style={{ 
                            border: '1px solid var(--success)', 
                            borderRadius: '4px', 
                            padding: '8px 24px 8px 16px',
                            color: 'var(--success)',
                            fontSize: '13px',
                            fontWeight: 500,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            backgroundColor: 'rgba(16, 185, 129, 0.05)',
                            minWidth: '80px',
                            position: 'relative'
                          }}>
                            {timeStr}
                            <button
                              onClick={(e) => { e.stopPropagation(); if(window.confirm('Delete this show?')) deleteShowMut.mutate(show.id); }}
                              style={{
                                position: 'absolute',
                                top: '4px',
                                right: '4px',
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--error)',
                                cursor: 'pointer',
                                fontSize: '10px',
                                padding: '2px',
                                opacity: 0.6
                              }}
                              title="Delete Show"
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {movieForm && (
        <div className="modal-overlay" onClick={() => setMovieForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🎬 Add New Movie</div>
            <form onSubmit={e => { e.preventDefault(); movieMut.mutate(mForm); }}>
              <div className="form-group"><label className="form-label">Title</label><input className="form-input" value={mForm.title} onChange={e => setMForm(p => ({ ...p, title: e.target.value }))} required /></div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Language</label><input className="form-input" value={mForm.language} onChange={e => setMForm(p => ({ ...p, language: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Certificate</label>
                  <select className="form-select" value={mForm.certificate} onChange={e => setMForm(p => ({ ...p, certificate: e.target.value }))}>
                    <option>U</option><option>U/A</option><option>A</option><option>S</option>
                  </select>
                </div>
                <div className="form-group"><label className="form-label">Duration (mins)</label><input type="number" className="form-input" value={mForm.duration_minutes} onChange={e => setMForm(p => ({ ...p, duration_minutes: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Genre</label><input className="form-input" value={mForm.genre} onChange={e => setMForm(p => ({ ...p, genre: e.target.value }))} /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setMovieForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={movieMut.isPending}>Add Movie</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🎬 Schedule Show</div>
            <form onSubmit={e => { e.preventDefault(); showMut.mutate(form); }}>
              <div className="form-group"><label className="form-label">Screen</label>
                <select className="form-select" value={form.screen} onChange={e => setForm(p => ({ ...p, screen: e.target.value }))} required>
                  <option value="">Select Screen</option>
                  {screenList.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Movie</label>
                <select className="form-select" value={form.movie} onChange={e => setForm(p => ({ ...p, movie: e.target.value }))} required>
                  <option value="">Select Movie</option>
                  {movieList.map(m => <option key={m.id} value={m.id}>{m.title} ({m.language})</option>)}
                </select>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Show Date</label><input type="date" className="form-input" value={form.show_date} onChange={e => setForm(p => ({ ...p, show_date: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Start Time</label><input type="time" className="form-input" value={form.start_time} onChange={e => setForm(p => ({ ...p, start_time: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">End Time</label><input type="time" className="form-input" value={form.end_time} onChange={e => setForm(p => ({ ...p, end_time: e.target.value }))} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={showMut.isPending}>✅ Schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
