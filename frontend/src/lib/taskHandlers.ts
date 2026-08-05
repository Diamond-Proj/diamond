export async function getUserProfile(data: { identity_id: string }) {
  try {
    const { identity_id } = data;
    const response = await fetch(
      `/api/profile?identity_id=${encodeURIComponent(identity_id)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const responseData = await response.json();
    console.log('getUserProfile responseData:', responseData);
    return responseData;
  } catch (error) {
    console.error('Error in getUserProfile:', error);
    throw error;
  }
}

interface UpdateUserProfileData {
  identity_id: string;
  name?: string;
  email?: string;
  institution?: string;
}

export async function updateUserProfile(data: UpdateUserProfileData) {
  try {
    const response = await fetch(`/api/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const responseData = await response.json();
    console.log('  responseData:', responseData);
    return responseData;
  } catch (error) {
    console.error('Error in updateUserProfile:', error);
    throw error;
  }
}

export async function registerAllEndpoints() {
  try {
    const response = await fetch('/api/register_all_endpoints', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const responseData = await response.json();
    console.log('registerAllEndpoints responseData:', responseData);
    return responseData;
  } catch (error) {
    console.error('Error in registerAllEndpoints:', error);
    throw error;
  }
}

export async function loadAccountsPartitions(data: { endpoint_uuid: string }) {
  try {
    const response = await fetch('/api/load_accounts_partitions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const responseData = await response.json();
    console.log('loadAccountsPartitions responseData:', responseData);
    return responseData;
  } catch (error) {
    console.error('Error in loadAccountsPartitions:', error);
    throw error;
  }
}
