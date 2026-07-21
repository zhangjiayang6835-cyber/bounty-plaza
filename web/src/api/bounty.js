import { t } from 'i18next';

export const fetchBounties = async () => {
  try {
    const response = await fetch('/api/bounties');
    if (!response.ok) {
      throw new Error(t('common.error'));
    }
    return await response.json();
  } catch (error) {
    console.error(error);
    throw new Error(t('common.error'));
  }
};