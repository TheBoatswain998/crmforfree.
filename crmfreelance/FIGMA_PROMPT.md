# Figma Design Prompt - Freelance CRM

## Quick Brief

Design a modern, minimal CRM web application for freelancers to manage clients, projects, and payments. The interface should be clean, professional, and data-focused with English/Russian language support.

---

## Design Request

**Project**: Freelance CRM Web Application  
**Platform**: Web (Desktop-first, mobile-responsive)  
**Pages**: 10+ screens (authentication, dashboard, data management)  
**Style**: Modern, minimal, professional SaaS aesthetic  
**Audience**: Freelancers and solo entrepreneurs (25-45 years old)

---

## Core Pages Needed

### 1. Authentication (2 pages)
- **Login page**: Email, password, login button, language switcher (EN/RU)
- **Register page**: Name, email, password, confirm password, register button

### 2. Dashboard (1 page)
- Welcome header with user name
- 3 metric cards: Active Clients (count), Pending Payments (money amount), and a third optional metric
- Table showing upcoming project deadlines (3 rows max)
- Clean, scannable layout

### 3. Clients Management (3 pages)
- **List page**: Data table with columns (Name, Email, Contact, Status badge, Last Contact, Actions)
- **Add page**: Form with fields (Name*, Email*, Contact, Status dropdown, Notes textarea)
- **Edit page**: Same form pre-filled with existing data
- Include "Import CSV" button in list header

### 4. Projects Management (3 pages)
- **List page**: Table with columns (Title, Client, Status badge, Budget, Deadline, Actions)
- **Add page**: Form with fields (Title*, Client dropdown, Status, Budget, Deadline date picker, Description)
- **Edit page**: Same form pre-filled

### 5. Payments Management (2 pages)
- **List page**: Table with columns (Project, Client, Amount, Status badge, Due Date, Comment, Actions)
- **Add page**: Form with fields (Project dropdown*, Amount*, Status, Due Date, Comment)

---

## Design System Requirements

### Colors
- **Primary**: Professional blue (#0066CC or similar)
- **Success**: Green (#28A745) for paid status, positive actions
- **Warning**: Yellow/Orange (#FFC107) for pending items
- **Danger**: Red (#DC3545) for delete actions
- **Neutrals**: Light gray backgrounds (#F8F9FA), dark text (#212529)

### Typography
- Sans-serif font family (Inter, Roboto, or Open Sans)
- Clear hierarchy: Large bold headers, readable body text
- Monospace for numbers and amounts

### Status Badges (Color-coded pills)
- **Client status**: Active (green), Cold (yellow), Archived (gray)
- **Project status**: Discussion (blue), In Progress (purple), Paused (orange), Completed (green)
- **Payment status**: Pending (yellow), Partial (orange), Paid (green)

### Components Needed
- Primary and secondary buttons
- Form inputs (text, email, number, date picker, dropdown, textarea)
- Data tables with hover states
- Status badges/pills
- Metric cards
- Flash message notifications (success/error)
- Navigation bar with active state indicators
- Language switcher toggle (EN | RU)

---

## Layout Structure

### Header (appears on all pages after login)
- Left: App logo/name
- Center: Navigation links (Dashboard, Clients, Projects, Payments)
- Right: Export button, Language switcher (EN/RU), Logout link

### Content Area
- Page title (H1)
- Action buttons (Add Client, Import CSV, etc.)
- Main content (tables, forms, cards)
- Flash messages at top

### Forms
- Clear labels above inputs
- Required fields marked with *
- Save and Cancel buttons at bottom
- Validation error messages in red below fields

### Tables
- Alternating row backgrounds or subtle borders
- Hover highlight on rows
- Action buttons (Edit/Delete icons) in last column
- Empty states with friendly messages

---

## Interaction States

- **Buttons**: Default, hover, active, disabled
- **Form inputs**: Default, focus (blue border), error (red border)
- **Table rows**: Default, hover (light background)
- **Navigation links**: Default, active/current page (bold or underline)
- **Status badges**: Static, no interactions
- **Modals**: Delete confirmation dialogs

---

## Responsive Behavior

- **Desktop (1200px+)**: Full layout with sidebar navigation
- **Tablet (768-1199px)**: Compact layout, horizontal table scroll if needed
- **Mobile (<768px)**: Stack elements vertically, consider hamburger menu, forms full-width

---

## Accessibility

- High contrast text (WCAG AA: 4.5:1 ratio minimum)
- Keyboard navigation support (visible focus states)
- Form labels properly associated with inputs
- Clear error messages
- Icon buttons with labels or ARIA labels

---

## Localization Notes

- Design should accommodate both English and Russian text
- Russian text can be ~30% longer than English
- Use system that supports Cyrillic characters
- Language switcher always visible (EN | RU toggle in header)

---

## Design Inspiration

Similar to: Stripe Dashboard, Linear App, Notion tables, minimal SaaS admin panels

Keywords: Clean, data-focused, professional, trustworthy, minimal decoration

---

## Deliverables Requested

1. **Style Guide Page**: Colors (hex codes), typography scale, spacing system, component styles
2. **Component Library**: All reusable elements with variants (buttons, inputs, badges, cards)
3. **High-Fidelity Mockups**: All 10+ pages designed for desktop
4. **Mobile Versions**: At least Dashboard, Clients list, and Add client form
5. **Prototype** (optional): Basic click-through navigation flow
6. **Developer Handoff**: Exportable assets, specs, design tokens as CSS variables

---

## File Organization

Organize Figma file with clear pages:
1. Cover (project overview)
2. Style Guide
3. Components Library
4. Desktop Pages (all 10+ screens)
5. Mobile Pages (key screens)
6. Prototype/Flow

---

## Priority Order

1. **Phase 1**: Style guide + Dashboard + Clients list/add
2. **Phase 2**: Projects list/add + Payments list/add
3. **Phase 3**: Authentication pages + mobile versions

---

## Additional Notes

- Use a consistent icon set (Heroicons, Feather, Lucide recommended)
- Include empty states for each list/table ("No clients yet. Add your first one!")
- Keep visual hierarchy clear: important actions should stand out
- Minimize decorative elements—focus on data and functionality
- Ensure design is easy to implement with HTML/CSS/Flask templates

---

## Questions to Consider

1. Light mode only, or include dark mode?
2. Custom illustrations for empty states, or simple text?
3. Any specific brand colors or fonts to use?
4. Level of animation/micro-interactions desired (none, subtle, rich)?

---

**Estimated Scope**: 10-12 unique screens + component library + mobile versions  
**Target Timeline**: 2-3 weeks (with 1-2 revision rounds)  
**Output Format**: Figma file with designs ready for developer handoff
