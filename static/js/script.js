// Show flash messages as toast notifications
document.querySelectorAll('.toast').forEach(t => new bootstrap.Toast(t, { delay: 4000 }).show());

// Default date inputs to today
document.querySelectorAll('input[type=date][data-today]').forEach(i => {
  if (!i.value) i.value = new Date().toISOString().slice(0, 10);
});

// Employee add/edit modal: fill fields from the clicked button's data-* attributes
const empModal = document.getElementById('empModal');
if (empModal) {
  empModal.addEventListener('show.bs.modal', ev => {
    const d = ev.relatedTarget.dataset, f = empModal.querySelector('form');
    f.reset();
    f.employee_id.value = d.id || '';
    if (d.id) {
      f.employee_name.value = d.name; f.email.value = d.email; f.phone.value = d.phone;
      f.department_id.value = d.dept; f.designation.value = d.designation;
      f.joining_date.value = d.joined; f.status.value = d.status;
    }
    empModal.querySelector('.modal-title').textContent = d.id ? 'Edit Employee' : 'Add Employee';
  });
}
