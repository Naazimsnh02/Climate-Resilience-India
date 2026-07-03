import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/overview", label: "Overview", icon: "◧" },
  { to: "/districts", label: "Districts", icon: "▤" },
  { to: "/farmer", label: "Farmer Advisory", icon: "🌾" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => (isActive ? "sidebar__link sidebar__link--active" : "sidebar__link")}
          >
            <span className="sidebar__icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
