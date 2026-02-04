# Freelance CRM - Design Brief for Figma

## Project Overview

A lightweight CRM web application for freelancers to manage clients, projects, and payments. The interface should be clean, professional, and easy to navigate with support for English and Russian languages.

## Target Users

- Freelancers
- Solo entrepreneurs
- Small agencies (1-5 people)
- Age range: 25-45
- Tech-savvy but prioritize simplicity

## Design Style

- **Aesthetic**: Modern, minimal, professional
- **Mood**: Trustworthy, efficient, organized
- **Approach**: Data-dense but not overwhelming
- **Mobile**: Responsive design required (desktop-first, mobile-friendly)

## Color Palette Suggestions

- **Primary**: Blue (#0066CC or similar) - trust, professionalism
- **Success**: Green (#28A745) - for payments, positive actions
- **Warning**: Orange/Yellow (#FFC107) - for pending items
- **Danger**: Red (#DC3545) - for delete actions, overdue items
- **Neutral**: Grays (#F8F9FA, #6C757D, #212529) - backgrounds, text
- **White**: Clean backgrounds

## Typography

- **Headers**: Sans-serif, bold, clean (e.g., Inter, Roboto, Open Sans)
- **Body**: Same family, regular weight
- **Monospace**: For numbers, amounts, dates

## Pages to Design

### 1. Authentication Pages

#### 1.1 Login Page
**Route**: `/login`

**Elements**:
- App logo/name at top
- Email input field
- Password input field
- "Login" primary button
- "Register" link below
- Language switcher (EN/RU) in top-right corner
- Clean centered layout with minimal distractions

**States**: Default, error messages (invalid credentials, empty fields)

#### 1.2 Registration Page
**Route**: `/register`

**Elements**:
- Name input field
- Email input field
- Password input field
- Confirm Password input field
- "Register" primary button
- "Already have an account? Login" link
- Language switcher (EN/RU)

**States**: Default, error messages (passwords don't match, email exists, validation errors)

---

### 2. Main Layout (After Login)

**Components**:

#### 2.1 Header
- App name/logo (left)
- Navigation menu (Dashboard, Clients, Projects, Payments)
- Export button (icon + text)
- Language switcher (EN | RU)
- Logout button/link (right)
- Active page indicator (highlight/underline)

#### 2.2 Content Area
- Page title (H1)
- Action buttons (Add Client, Add Project, etc.)
- Main content (tables, cards, forms)
- Flash messages area (success/error notifications)

---

### 3. Dashboard Page
**Route**: `/dashboard`

**Layout**:
- Welcome message: "Hello, [User Name]!"
- 3 metric cards in a row (responsive: stack on mobile):

**Card 1**: Active Clients
- Icon: User/People icon
- Large number display
- Label: "Active Clients"

**Card 2**: Pending Payments
- Icon: Dollar/Money icon
- Large number display (with currency format)
- Label: "Pending Payments"
- Green/money color accent

**Card 3** (optional): Total Projects or similar metric

**Section**: Upcoming Deadlines
- Table with 3 columns: Project | Client | Deadline
- Shows top 3 closest deadlines
- Empty state: "No upcoming deadlines."

---

### 4. Clients Page
**Route**: `/clients`

**Header Actions**:
- "Add Client" primary button (green/blue)
- "Import CSV" secondary button with file upload icon
- CSV import modal/form (file picker)

**Table Columns**:
1. Name
2. Email
3. Contact
4. Status (badge: active=green, cold=yellow, archived=gray)
5. Last Contact (date)
6. Actions (Edit icon button, Delete icon button)

**Empty State**: "No clients yet. Add your first one!"

**Status Badges**: Color-coded pills
- Active: Green background
- Cold: Yellow/orange background
- Archived: Gray background

---

### 5. Add/Edit Client Forms
**Routes**: `/clients/add`, `/clients/edit/<id>`

**Form Fields**:
- Name* (required, text input)
- Email* (required, email input)
- Contact (text input, phone format optional)
- Status (dropdown: Active, Cold, Archived)
- Notes (textarea, multi-line)

**Buttons**:
- "Save" primary button
- "Cancel" secondary button (link back)

**Validation**: Show error messages inline for required fields

---

### 6. Projects Page
**Route**: `/projects`

**Header Actions**:
- "Add Project" primary button

**Table Columns**:
1. Title
2. Client (linked client name or "—")
3. Status (badge: discussion, in progress, paused, completed)
4. Budget (formatted number)
5. Deadline (date, highlight if < 7 days)
6. Actions (Edit, Delete)

**Status Badges**:
- Discussion: Blue
- In Progress: Purple/Blue
- Paused: Orange
- Completed: Green

**Empty State**: "No projects yet."

---

### 7. Add/Edit Project Forms
**Routes**: `/projects/add`, `/projects/edit/<id>`

**Form Fields**:
- Title* (required)
- Client (dropdown: "-- no client --" + list of user's clients)
- Status (dropdown: Discussion, In Progress, Paused, Completed)
- Budget (number input with currency symbol)
- Deadline (date picker)
- Description (textarea)

**Buttons**: Save, Cancel

---

### 8. Payments Page
**Route**: `/payments`

**Header Actions**:
- "Add Payment" primary button

**Table Columns**:
1. Project (linked project title)
2. Client (from project relationship)
3. Amount (bold, formatted currency)
4. Status (badge: pending=yellow, partial=orange, paid=green)
5. Due Date
6. Comment (truncated if long)
7. Actions (Delete only)

**Status Badges**:
- Pending: Yellow/orange
- Partial: Orange
- Paid: Green

**Empty State**: "No payments yet."

---

### 9. Add Payment Form
**Route**: `/payments/add`

**Form Fields**:
- Project* (dropdown: "-- select project --" + list with format "Project Name (Client Name)")
- Amount* (number input, currency)
- Status (dropdown: Pending, Partial, Paid)
- Due Date (date picker)
- Comment (textarea, optional)

**Buttons**: Save, Cancel

---

### 10. Export Feature
**Route**: `/export` (download action)

**Design**:
- Can be a button in header/nav
- Icon: Download or Export icon
- On click: Downloads ZIP file (no separate page needed)
- Optional: Show toast notification "Export started..." / "Export complete"

---

## UI Components Library Needed

### Buttons
- Primary button (solid color)
- Secondary button (outline or ghost)
- Danger button (red, for delete)
- Icon buttons (small, for actions in tables)

### Form Elements
- Text input
- Email input
- Number input
- Textarea
- Dropdown/select
- Date picker
- File upload (for CSV import)

### Data Display
- Tables (sortable headers optional)
- Metric cards
- Status badges/pills
- Empty states

### Feedback
- Flash messages (success=green, error=red, info=blue)
- Form validation errors (inline, red text)
- Confirmation dialogs (for delete actions)
- Loading states

### Navigation
- Top navigation bar
- Active link indicators
- Breadcrumbs (optional)

---

## Responsive Breakpoints

- **Desktop**: 1200px+ (default)
- **Tablet**: 768px - 1199px (table scrolls horizontally if needed)
- **Mobile**: < 768px (stack cards, hamburger menu optional, prioritize forms)

---

## Interactions & States

### Hover States
- Buttons: Slight color change, elevation
- Table rows: Light background highlight
- Links: Underline or color change

### Active States
- Navigation: Bold text, underline, or background highlight
- Buttons: Pressed/active state

### Focus States
- Form inputs: Blue border or outline
- Accessible keyboard navigation

### Loading States
- Button: Show spinner, disable interaction
- Page: Loading indicator or skeleton screens

### Delete Confirmation
- Modal or inline confirmation: "Delete this [item]?" with "Confirm" and "Cancel"

---

## Accessibility Requirements

- Color contrast ratio: WCAG AA minimum (4.5:1 for text)
- Keyboard navigation support
- Form labels properly associated
- Error messages clearly visible
- Focus indicators visible
- Alt text for icons (use ARIA labels)

---

## Localization (i18n)

All text content must be in **both English and Russian**. Design should accommodate:
- Longer Russian text (roughly 30% more space)
- Cyrillic characters rendering properly
- Language switcher always visible and easy to toggle

---

## Figma Deliverables

### Must Have:
1. **Style Guide Page**:
   - Color palette with hex codes
   - Typography scale (H1, H2, H3, Body, Caption)
   - Spacing system (8px grid or similar)
   - Button styles
   - Form element styles
   - Status badge styles

2. **Component Library**:
   - All reusable components (buttons, inputs, cards, badges, tables)
   - Component variants (hover, active, disabled states)

3. **Full Page Designs** (Desktop):
   - Login page
   - Register page
   - Dashboard
   - Clients list
   - Add/Edit client
   - Projects list
   - Add/Edit project
   - Payments list
   - Add payment

4. **Mobile Versions** (at least 3 key pages):
   - Dashboard
   - Clients list
   - Add client form

5. **Interactive Prototype** (optional but recommended):
   - Basic navigation flow
   - Form interactions
   - Modal/dialog interactions

---

## Design Inspiration Keywords

- **For research**: SaaS dashboard, CRM interface, project management, minimal admin panel, Stripe dashboard, Linear app, Notion database view
- **Style**: Clean, data-focused, minimal decoration, professional, trustworthy

---

## Technical Notes for Developer

- Designs should be exportable as SVG/PNG assets
- Icon set should be consistent (recommend: Heroicons, Feather Icons, Lucide)
- Use web-safe fonts or provide Google Fonts links
- Provide design tokens (CSS variables) for colors, spacing, typography
- Ensure designs work well with HTML tables (for data display)

---

## Questions for Designer

1. Do you prefer a specific color scheme (light mode only, or dark mode too)?
2. Should we include animations/micro-interactions?
3. Do you want custom illustrations for empty states, or simple text?
4. Any brand guidelines or existing visual identity to follow?

---

## Figma File Structure Suggestion

```
📁 Freelance CRM Design
  📄 01 - Cover (Project overview)
  📄 02 - Style Guide (Colors, Typography, Components)
  📄 03 - Components (All reusable elements)
  📄 04 - Pages - Desktop (All page designs)
  📄 05 - Pages - Mobile (Mobile responsive versions)
  📄 06 - Prototype Flow (Interactive states)
  📄 07 - Developer Handoff (Specs, exports)
```

---

## Next Steps

1. Designer creates initial style guide (colors, fonts, basic components)
2. Review and approve style direction
3. Designer creates 2-3 key pages (Dashboard, Clients, Add Client)
4. Iterate based on feedback
5. Complete remaining pages
6. Developer handoff with specs and assets

---

**Estimated Design Timeline**: 2-3 weeks (depends on revisions)
**Priority Pages**: Dashboard → Clients → Projects → Payments → Auth pages
