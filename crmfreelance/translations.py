"""
Internationalization module for Freelance CRM
Supports: English (en), Russian (ru)
"""

TRANSLATIONS = {
    'en': {
        # General
        'crm_ready': 'CRM ready',
        'welcome': 'Welcome',
        'hello': 'Hello',
        
        # Navigation
        'dashboard': 'Dashboard',
        'clients': 'Clients',
        'projects': 'Projects',
        'payments': 'Payments',
        'export': 'Export',
        'logout': 'Logout',
        'login': 'Login',
        'register': 'Register',
        
        # Form labels
        'email': 'Email',
        'password': 'Password',
        'confirm_password': 'Confirm Password',
        'name': 'Name',
        'status': 'Status',
        'contact': 'Contact',
        'notes': 'Notes',
        'last_contact': 'Last Contact',
        'actions': 'Actions',
        'title': 'Title',
        'client': 'Client',
        'budget': 'Budget',
        'deadline': 'Deadline',
        'description': 'Description',
        'amount': 'Amount',
        'due_date': 'Due Date',
        'comment': 'Comment',
        'project': 'Project',
        
        # Buttons
        'submit': 'Submit',
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'send': 'Send',
        'complete': 'Complete',
        'mark_paid': 'Mark as Paid',
        
        # Dashboard
        'active_clients': 'Active Clients',
        'pending_payments': 'Pending Payments',
        'upcoming_deadlines': 'Upcoming Deadlines',
        'no_deadlines': 'No upcoming deadlines.',
        
        # Empty states
        'no_clients': 'No clients yet. Add your first one!',
        'no_projects': 'No projects yet.',
        'no_payments': 'No payments yet.',
        
        # Page titles
        'add_client': 'Add Client',
        'add_project': 'Add Project',
        'add_payment': 'Add Payment',
        'edit_client': 'Edit Client',
        'edit_project': 'Edit Project',
        
        # Form options
        'import_csv': 'Import CSV',
        'select_file': 'Select file',
        'no_client': '-- no client --',
        'select_project': '-- select project --',
        
        # Validation messages
        'fill_required': 'Please fill in all required fields',
        'passwords_mismatch': 'Passwords do not match',
        'email_exists': 'Email already in use',
        'invalid_email': 'Invalid email format',
        'invalid_credentials': 'Invalid email or password',
        'title_required': 'Title is required',
        'name_email_required': 'Name and Email are required',
        'project_amount_required': 'Project and Amount are required',
        'select_existing_client': 'Select an existing client',
        'select_existing_project': 'Select an existing project',
        
        # Success messages
        'logged_out': 'You have been logged out',
        'client_added': 'Client added',
        'client_updated': 'Client updated',
        'client_deleted': 'Client deleted',
        'project_added': 'Project added',
        'project_updated': 'Project updated',
        'project_deleted': 'Project deleted',
        'project_completed': 'Project marked as completed',
        'payment_added': 'Payment added',
        'payment_deleted': 'Payment deleted',
        'payment_marked_paid': 'Payment marked as paid',
        
        # Error messages
        'db_error': 'Database error',
        'client_not_found': 'Client not found or access denied',
        'project_not_found': 'Project not found or access denied',
        'payment_not_found': 'Payment not found or access denied',
        'file_not_selected': 'File not selected',
        'invalid_csv': 'Invalid CSV format',
        'csv_missing_columns': 'Invalid CSV: missing required columns (name, email)',
        'imported_clients': 'Imported {count} clients',
        'skipped_rows': 'Skipped {count} rows (duplicates or empty)',
        
        # Confirmations
        'confirm_delete_client': 'Delete this client?',
        'confirm_delete_project': 'Delete this project?',
        'confirm_delete_payment': 'Delete this payment?',
        
        # Status values
        'active': 'active',
        'cold': 'cold',
        'archived': 'archived',
        'discussion': 'discussion',
        'in_progress': 'in progress',
        'paused': 'paused',
        'completed': 'completed',
        'pending': 'pending',
        'partial': 'partial',
        'paid': 'paid',
        
        # Export headers
        'client_name': 'Client Name',
        'project_name': 'Project Name',
        'payment_status': 'Payment Status',
        
        # Feedback/Support
        'need_help': 'Need help? I\'m here — Pavel',
        'feedback_placeholder': 'Your feedback...',
        'describe_issue': 'Describe your issue...',
        'optional': 'optional',
        'sent': 'Sent',
    },
    
    'ru': {
        # General
        'crm_ready': 'CRM готов',
        'welcome': 'Добро пожаловать',
        'hello': 'Привет',
        
        # Navigation
        'dashboard': 'Дашборд',
        'clients': 'Клиенты',
        'projects': 'Проекты',
        'payments': 'Платежи',
        'export': 'Экспорт',
        'logout': 'Выйти',
        'login': 'Вход',
        'register': 'Регистрация',
        
        # Form labels
        'email': 'Email',
        'password': 'Пароль',
        'confirm_password': 'Подтвердите пароль',
        'name': 'Имя',
        'status': 'Статус',
        'contact': 'Контакт',
        'notes': 'Заметки',
        'last_contact': 'Последний контакт',
        'actions': 'Действия',
        'title': 'Название',
        'client': 'Клиент',
        'budget': 'Бюджет',
        'deadline': 'Дедлайн',
        'description': 'Описание',
        'amount': 'Сумма',
        'due_date': 'Срок оплаты',
        'comment': 'Комментарий',
        'project': 'Проект',
        
        # Buttons
        'submit': 'Отправить',
        'add': 'Добавить',
        'edit': 'Редактировать',
        'delete': 'Удалить',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'send': 'Отправить',
        'complete': 'Завершить',
        'mark_paid': 'Отметить оплаченным',
        
        # Dashboard
        'active_clients': 'Активные клиенты',
        'pending_payments': 'Ожидаемо к оплате',
        'upcoming_deadlines': 'Ближайшие дедлайны',
        'no_deadlines': 'Нет предстоящих дедлайнов.',
        
        # Empty states
        'no_clients': 'Клиентов пока нет. Добавьте первого!',
        'no_projects': 'Проектов пока нет.',
        'no_payments': 'Платежей пока нет.',
        
        # Page titles
        'add_client': 'Добавить клиента',
        'add_project': 'Добавить проект',
        'add_payment': 'Добавить платёж',
        'edit_client': 'Редактировать клиента',
        'edit_project': 'Редактировать проект',
        
        # Form options
        'import_csv': 'Импорт CSV',
        'select_file': 'Выберите файл',
        'no_client': '-- без клиента --',
        'select_project': '-- выберите проект --',
        
        # Validation messages
        'fill_required': 'Пожалуйста, заполните все обязательные поля',
        'passwords_mismatch': 'Пароли не совпадают',
        'email_exists': 'Email уже используется',
        'invalid_email': 'Неверный формат email',
        'invalid_credentials': 'Неверный email или пароль',
        'title_required': 'Поле Название обязательно',
        'name_email_required': 'Поля Имя и Email обязательны',
        'project_amount_required': 'Поля Проект и Сумма обязательны',
        'select_existing_client': 'Выберите существующего клиента',
        'select_existing_project': 'Выберите существующий проект',
        
        # Success messages
        'logged_out': 'Вы вышли',
        'client_added': 'Клиент добавлен',
        'client_updated': 'Клиент обновлён',
        'client_deleted': 'Клиент удалён',
        'project_added': 'Проект добавлен',
        'project_updated': 'Проект обновлён',
        'project_deleted': 'Проект удалён',
        'project_completed': 'Проект отмечен как завершённый',
        'payment_added': 'Платёж добавлен',
        'payment_deleted': 'Платёж удалён',
        'payment_marked_paid': 'Платёж отмечен как оплаченный',
        
        # Error messages
        'db_error': 'Ошибка базы данных',
        'client_not_found': 'Клиент не найден или доступ запрещён',
        'project_not_found': 'Проект не найден или доступ запрещён',
        'payment_not_found': 'Платёж не найден или доступ запрещён',
        'file_not_selected': 'Файл не выбран',
        'invalid_csv': 'Неверный формат CSV',
        'csv_missing_columns': 'Неверный формат CSV: отсутствуют обязательные колонки (name, email)',
        'imported_clients': 'Импортировано {count} клиентов',
        'skipped_rows': 'Пропущено {count} строк (дубликаты или пустые)',
        
        # Confirmations
        'confirm_delete_client': 'Удалить клиента?',
        'confirm_delete_project': 'Удалить проект?',
        'confirm_delete_payment': 'Удалить платёж?',
        
        # Status values
        'active': 'активный',
        'cold': 'холодный',
        'archived': 'архив',
        'discussion': 'обсуждение',
        'in_progress': 'в работе',
        'paused': 'пауза',
        'completed': 'завершён',
        'pending': 'ожидает',
        'partial': 'частично',
        'paid': 'оплачен',
        
        # Export headers
        'client_name': 'Имя клиента',
        'project_name': 'Название проекта',
        'payment_status': 'Статус оплаты',
        
        # Feedback/Support
        'need_help': 'Нужна помощь? Я здесь — Павел',
        'feedback_placeholder': 'Ваш отзыв...',
        'describe_issue': 'Опишите проблему...',
        'optional': 'опционально',
        'sent': 'Отправлено',
    }
}


def get_text(key, lang='en', **kwargs):
    """
    Get translated text for the given key.
    Falls back to English if key not found in requested language.
    Supports string formatting with kwargs.
    """
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
