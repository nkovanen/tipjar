'use strict';
// A README badge opens onboarding for this repository; it never starts work.
const invitation = document.getElementById('repository-invitation');
const requestedRepository = new URLSearchParams(location.search).get('repo');
if (requestedRepository !== null) {
  invitation.hidden = false;
  try {
    TipjarModel.makeBadge(requestedRepository); // Share the local repository validation.
    const repository = requestedRepository.toLowerCase();
    const link = document.createElement('a');
    link.textContent = 'Prepare README invitation for ' + repository + ' ↗';
    link.href = 'directory.html?repo=' + encodeURIComponent(repository) + '#maintainers';
    invitation.append(link);
  } catch {
    invitation.textContent = 'Invalid repository parameter: ' + requestedRepository;
  }
}
