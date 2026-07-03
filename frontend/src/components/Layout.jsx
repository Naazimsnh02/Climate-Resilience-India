import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <img src="/logo_transparent.png" className="app-header__logo" alt="Climate Resilience India Logo" />
          <span className="app-header__title">El Niño 2026 Decision Copilot</span>
        </div>
        <nav className="app-header__nav">
          <NavLink to="/admin" className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}>
            Admin Console
          </NavLink>
          <NavLink to="/farmer" className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}>
            Farmer Advisory
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
